import uuid
from typing import Dict, Any
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.facility import Facility
from app.models.ivr import IVRSession
from app.models.medicine import Medicine


@pytest.mark.asyncio
async def test_ivr_start_and_menu_navigation(client: AsyncClient, seed_data: Dict[str, Any]):
    """Test standard call initiation and DTMF navigation across public menus."""
    headers = {"X-API-Key": settings.IVR_API_KEY}
    caller_phone = "9876543203"

    # 1. Start call
    start_res = await client.post(
        "/api/ivr/call/start",
        json={"caller_phone": caller_phone},
        headers=headers,
    )
    assert start_res.status_code == 201
    call_data = start_res.json()
    call_sid = call_data["call_sid"]
    assert "CareBridge" in call_data["speak_text"]
    assert call_data["current_menu"] == "LANGUAGE_SELECT"

    # 2. Select English (press 2)
    step1 = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "2"},
        headers=headers,
    )
    assert step1.status_code == 200
    s1_data = step1.json()
    assert s1_data["current_menu"] == "MAIN_MENU"
    assert s1_data["language"] == "en"
    assert "Main Menu" in s1_data["speak_text"]

    # 3. Choose Option 1 (Find Nearby Facilities)
    step2 = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "1"},
        headers=headers,
    )
    assert step2.status_code == 200
    s2_data = step2.json()
    assert s2_data["current_menu"] == "FACILITIES_LIST"
    assert "PHC" in s2_data["speak_text"] or "hospital" in s2_data["speak_text"].lower()

    # 4. Choose 0 or any key to return to Main Menu
    step3 = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "0"},
        headers=headers,
    )
    assert step3.status_code == 200
    s3_data = step3.json()
    assert s3_data["current_menu"] == "MAIN_MENU"

    # 5. Choose Option 2 (Doctor Availability)
    step4 = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "2"},
        headers=headers,
    )
    assert step4.status_code == 200
    assert "dr." in step4.json()["speak_text"].lower() or "doctor" in step4.json()["speak_text"].lower()

    # 6. Return to Main Menu (press 0)
    step5 = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "0"},
        headers=headers,
    )
    assert step5.status_code == 200
    assert step5.json()["current_menu"] == "MAIN_MENU"

    # 7. Choose Option 3 (Medicine Stock Check)
    step6 = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "3"},
        headers=headers,
    )
    assert step6.status_code == 200
    s6_data = step6.json()
    assert s6_data["current_menu"] == "MEDICINE_SELECT"
    assert "medicine" in s6_data["speak_text"].lower()

    # 8. Choose first medicine (press 1)
    step7 = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "1"},
        headers=headers,
    )
    assert step7.status_code == 200
    s7_data = step7.json()
    assert s7_data["current_menu"] == "MAIN_MENU"
    assert "availability" in s7_data["speak_text"].lower() or "likely" in s7_data["speak_text"].lower() or "uncertain" in s7_data["speak_text"].lower()

    # 9. Choose Option 7 (Emergency 108 Guidance)
    step8 = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "7"},
        headers=headers,
    )
    assert step8.status_code == 200
    assert "108" in step8.json()["speak_text"]


@pytest.mark.asyncio
async def test_ivr_session_status_and_hangup(client: AsyncClient, db_session: AsyncSession):
    """Test retrieving session status and ending a call."""
    headers = {"X-API-Key": settings.IVR_API_KEY}

    start_res = await client.post(
        "/api/ivr/call/start",
        json={"caller_phone": "9876543203"},
        headers=headers,
    )
    call_sid = start_res.json()["call_sid"]

    # Query session from database to find its UUID
    stmt = select(IVRSession).where(IVRSession.call_sid == call_sid)
    res = await db_session.execute(stmt)
    session = res.scalar_one()

    # Check status endpoint
    status_res = await client.get(f"/api/ivr/session/{session.id}", headers=headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["id"] == str(session.id)
    assert status_data["call_sid"] == call_sid
    assert status_data["status"] == "IN_PROGRESS"
    assert status_data["is_verified"] is False

    # Terminate call via hangup endpoint
    hangup_res = await client.post(
        "/api/ivr/call/hangup",
        json={"call_sid": call_sid, "digits": ""},
        headers=headers,
    )
    assert hangup_res.status_code == 200
    hangup_data = hangup_res.json()
    assert hangup_data["hangup"] is True
    assert hangup_data["session_status"] == "COMPLETED"

    # Verify session is now COMPLETED
    await db_session.refresh(session)
    assert session.status == "COMPLETED"
    assert session.ended_at is not None


@pytest.mark.asyncio
async def test_ivr_twilio_twiml_webhook(client: AsyncClient, monkeypatch):
    """Test Twilio form-data webhook returning TwiML XML."""
    headers = {"X-API-Key": settings.IVR_API_KEY}
    monkeypatch.setattr(settings, "IVR_PROVIDER", "twilio")

    # Inbound call event from Twilio (POST with form URL-encoded body)
    twilio_start = await client.post(
        "/api/ivr/webhook",
        data={
            "CallSid": "CA_twilio_test_1001",
            "From": "+919876543203",
            "CallStatus": "ringing",
        },
        headers=headers,
    )
    assert twilio_start.status_code == 200
    assert twilio_start.headers["content-type"].startswith("application/xml")
    xml_content = twilio_start.text
    assert "<Response>" in xml_content
    assert "<Gather" in xml_content
    assert "<Say" in xml_content
    assert "CareBridge" in xml_content

    # Keypress callback event from Twilio (Gather result)
    twilio_input = await client.post(
        "/api/ivr/webhook",
        data={
            "CallSid": "CA_twilio_test_1001",
            "From": "+919876543203",
            "Digits": "1",  # Select Tamil
        },
        headers=headers,
    )
    assert twilio_input.status_code == 200
    assert twilio_input.headers["content-type"].startswith("application/xml")
    input_xml = twilio_input.text
    assert "<Response>" in input_xml
    assert "முதன்மை மெனு" in input_xml


@pytest.mark.asyncio
async def test_ivr_api_contract_lookup_and_feedback(client: AsyncClient, seed_data: Dict[str, Any]):
    """Test API.md Section 9 contract endpoints: /api/ivr/lookup and /api/ivr/feedback."""
    headers = {"X-API-Key": settings.IVR_API_KEY}
    patient_phone = seed_data["users"]["patient"].phone
    facility_id = seed_data["facilities"][0].id

    # 1. Lookup medicine availability for phone
    lookup_res = await client.post(
        "/api/ivr/lookup",
        json={"phone": patient_phone, "medicine_code": "paracetamol"},
        headers=headers,
    )
    assert lookup_res.status_code == 200
    lookup_data = lookup_res.json()
    assert "speak_text" in lookup_data
    assert "facility_id" in lookup_data
    assert 0.0 <= lookup_data["p_available"] <= 1.0
    assert "paracetamol" in lookup_data["speak_text"].lower() or "மருந்து" in lookup_data["speak_text"]

    # 2. Submit patient feedback via button phone
    feedback_res = await client.post(
        "/api/ivr/feedback",
        json={
            "phone": patient_phone,
            "facility_id": str(facility_id),
            "medicine_code": "paracetamol",
            "got_it": True,
        },
        headers=headers,
    )
    assert feedback_res.status_code == 200
    fb_data = feedback_res.json()
    assert fb_data["status"] == "RECORDED"
    assert "Thank you" in fb_data["message"] or "நன்றி" in fb_data["message"]
