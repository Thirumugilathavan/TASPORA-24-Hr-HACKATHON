import base64
import hashlib
import hmac
from typing import Any, Dict
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.integrations.telephony.twilio_provider import TwilioTelephonyProvider
from app.models.ivr import IVRSession
from app.models.request import HealthcareRequest
from app.schemas.shared import RequestType


def generate_twilio_signature(url: str, params: Dict[str, Any], auth_token: str) -> str:
    """Helper to compute valid Twilio HMAC-SHA1 signature for testing."""
    s = url
    for k in sorted(params.keys()):
        val = params[k]
        if isinstance(val, (list, tuple)):
            val = val[0] if val else ""
        s += f"{k}{val}"
    mac = hmac.new(auth_token.encode("utf-8"), s.encode("utf-8"), hashlib.sha1)
    return base64.b64encode(mac.digest()).decode("utf-8")


@pytest.mark.asyncio
async def test_twilio_signature_verification_unit():
    """Unit test Twilio HMAC-SHA1 signature validation."""
    provider = TwilioTelephonyProvider()
    token = "test_secret_auth_token_123"
    settings.TELEPHONY_AUTH_TOKEN = token

    url = "https://carebridge.org/api/ivr/webhooks/incoming"
    params = {"CallSid": "CA12345", "From": "+919876543201", "CallStatus": "ringing"}

    # Valid signature
    valid_sig = generate_twilio_signature(url, params, token)
    headers = {"X-Twilio-Signature": valid_sig}
    assert provider.validate_inbound_webhook(params, headers, url) is True

    # Invalid signature
    headers_bad = {"X-Twilio-Signature": "invalid_base64_sig"}
    assert provider.validate_inbound_webhook(params, headers_bad, url) is False

    # Missing signature
    assert provider.validate_inbound_webhook(params, {}, url) is False

    # Reset
    settings.TELEPHONY_AUTH_TOKEN = ""


@pytest.mark.asyncio
async def test_carrier_incoming_webhook_security(client: AsyncClient, monkeypatch):
    """Verify carrier incoming webhook rejects unauthorized requests with 403."""
    monkeypatch.setattr(settings, "TELEPHONY_PROVIDER", "twilio")
    monkeypatch.setattr(settings, "TELEPHONY_AUTH_TOKEN", "super_secret_auth_token_999")

    # Inbound call without signature
    res_no_sig = await client.post(
        "/api/ivr/webhooks/incoming",
        data={"CallSid": "CA_test_sec_01", "From": "+919876543203"},
    )
    assert res_no_sig.status_code == 403
    assert "Invalid telephony webhook signature" in res_no_sig.json()["error"]["message"]

    # Inbound call with invalid signature
    res_bad_sig = await client.post(
        "/api/ivr/webhooks/incoming",
        data={"CallSid": "CA_test_sec_01", "From": "+919876543203"},
        headers={"X-Twilio-Signature": "bogus_signature=="},
    )
    assert res_bad_sig.status_code == 403


@pytest.mark.asyncio
async def test_carrier_inbound_and_continue_flow(client: AsyncClient, monkeypatch, db_session: AsyncSession):
    """Test full carrier incoming call, DTMF continue, and TwiML generation."""
    monkeypatch.setattr(settings, "TELEPHONY_PROVIDER", "twilio")
    monkeypatch.setattr(settings, "TELEPHONY_AUTH_TOKEN", "")  # local bypass

    # 1. Incoming Call Webhook
    call_sid = "CA_carrier_flow_101"
    res1 = await client.post(
        "/api/ivr/webhooks/incoming",
        data={"CallSid": call_sid, "From": "+919876543203"},
    )
    assert res1.status_code == 200
    assert "application/xml" in res1.headers["content-type"]
    xml1 = res1.text
    assert "<Response>" in xml1
    assert "<Gather" in xml1
    assert 'action="/api/ivr/webhooks/continue"' in xml1
    assert "CareBridge" in xml1

    # 2. Continue Webhook (Select Tamil - Digits: 1)
    res2 = await client.post(
        "/api/ivr/webhooks/continue",
        data={"CallSid": call_sid, "From": "+919876543203", "Digits": "1"},
    )
    assert res2.status_code == 200
    xml2 = res2.text
    assert "முதன்மை மெனு" in xml2
    assert 'language="ta-IN"' in xml2

    # 3. Emergency Key (Digits: 7) - Immediate 108 guidance without auth
    res3 = await client.post(
        "/api/ivr/webhooks/continue",
        data={"CallSid": call_sid, "From": "+919876543203", "Digits": "7"},
    )
    assert res3.status_code == 200
    xml3 = res3.text
    assert "108" in xml3

    # 4. Status Webhook - Hangup / Call Completed
    res4 = await client.post(
        "/api/ivr/webhooks/status",
        data={"CallSid": call_sid, "CallStatus": "completed", "CallDuration": "42"},
    )
    assert res4.status_code == 200
    assert res4.json()["status"] == "ACKNOWLEDGED"

    # Verify session marked COMPLETED in database
    stmt = select(IVRSession).where(IVRSession.call_sid == call_sid)
    sess_res = await db_session.execute(stmt)
    session = sess_res.scalar_one()
    assert session.status == "COMPLETED"


@pytest.mark.asyncio
async def test_call_transfer_twiml(client: AsyncClient, monkeypatch):
    """Test Call Transfer TwiML generation when caller presses 0 from main menu."""
    monkeypatch.setattr(settings, "TELEPHONY_PROVIDER", "twilio")
    monkeypatch.setattr(settings, "TELEPHONY_AUTH_TOKEN", "")
    monkeypatch.setattr(settings, "IVR_ENABLE_CALL_TRANSFER", True)
    monkeypatch.setattr(settings, "IVR_TRANSFER_PHONE_NUMBER", "+919876500999")

    call_sid = "CA_transfer_test_202"
    # Initiate call
    await client.post(
        "/api/ivr/webhooks/incoming",
        data={"CallSid": call_sid, "From": "+919876543203"},
    )
    # Select English (2)
    await client.post(
        "/api/ivr/webhooks/continue",
        data={"CallSid": call_sid, "From": "+919876543203", "Digits": "2"},
    )
    # Press 0 from Main Menu -> Triggers transfer
    res = await client.post(
        "/api/ivr/webhooks/continue",
        data={"CallSid": call_sid, "From": "+919876543203", "Digits": "0"},
    )
    assert res.status_code == 200
    xml = res.text
    assert "<Dial" in xml
    assert "+919876500999" in xml


@pytest.mark.asyncio
async def test_asha_callback_request_flow(client: AsyncClient, seed_data: Dict[str, Any], db_session: AsyncSession):
    """Test authenticated patient requesting ASHA callback assistance (Option 5 in request menu)."""
    headers = {"X-API-Key": settings.IVR_API_KEY}
    patient = seed_data["users"]["patient"]
    phone = patient.phone
    pin = phone[-4:]

    call_sid = "CA_asha_callback_303"
    # 1. Start call
    await client.post("/api/ivr/call/start", json={"caller_phone": phone, "call_sid": call_sid}, headers=headers)
    # 2. Select Tamil (1)
    await client.post("/api/ivr/call/input", json={"call_sid": call_sid, "digits": "1"}, headers=headers)
    # 3. Option 4 (Healthcare Request / Assistance) -> PIN prompt
    await client.post("/api/ivr/call/input", json={"call_sid": call_sid, "digits": "4"}, headers=headers)
    # 4. Enter PIN
    await client.post("/api/ivr/call/input", json={"call_sid": call_sid, "digits": pin}, headers=headers)
    # 5. Select Request Type 5: ASHA Worker Callback
    res_type = await client.post("/api/ivr/call/input", json={"call_sid": call_sid, "digits": "5"}, headers=headers)
    assert res_type.json()["current_menu"] == "REQUEST_URGENCY_SELECT"
    # 6. Select Urgency 2 (Priority)
    res_urg = await client.post("/api/ivr/call/input", json={"call_sid": call_sid, "digits": "2"}, headers=headers)
    assert res_urg.status_code == 200
    assert "ஆஷா" in res_urg.json()["speak_text"]
    assert "பதிவு செய்யப்பட்டது" in res_urg.json()["speak_text"]

    # Verify HealthcareRequest created in DB with ASHA description
    req_stmt = select(HealthcareRequest).where(HealthcareRequest.description.contains("ASHA worker callback"))
    req_res = await db_session.execute(req_stmt)
    req = req_res.scalars().first()
    assert req is not None
    assert req.request_type == RequestType.CONSULTATION


@pytest.mark.asyncio
async def test_outbound_call_dispatch(client: AsyncClient):
    """Test outbound callback dispatch API."""
    headers = {"X-API-Key": settings.IVR_API_KEY}

    # Dispatch outbound call to patient
    res = await client.post(
        "/api/ivr/callbacks/initiate",
        json={"to_phone": "9876543203", "purpose": "ASHA_CALLBACK"},
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["to_phone"] == "9876543203"
    assert data["status"] in ("queued", "in-progress")
    assert "call_sid" in data

    # Test invalid phone rejection
    res_bad = await client.post(
        "/api/ivr/callbacks/initiate",
        json={"to_phone": "123", "purpose": "ASHA_CALLBACK"},
        headers=headers,
    )
    assert res_bad.status_code == 400
