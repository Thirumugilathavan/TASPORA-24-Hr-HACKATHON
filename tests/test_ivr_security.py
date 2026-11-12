import uuid
import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.asyncio
async def test_ivr_missing_api_key_returns_401(client: AsyncClient):
    """Calling IVR endpoints without X-API-Key must return 401 Unauthorized."""
    endpoints = [
        ("POST", "/api/ivr/call/start", {"caller_phone": "9876543203"}),
        ("POST", "/api/ivr/webhook", {"CallSid": "CA12345678", "From": "+919876543203"}),
        ("POST", "/api/ivr/lookup", {"phone": "9876543203", "medicine_code": "paracetamol"}),
        ("POST", "/api/ivr/feedback", {"phone": "9876543203", "facility_id": str(uuid.uuid4()), "medicine_code": "paracetamol", "got_it": True}),
    ]

    for method, path, payload in endpoints:
        if method == "POST":
            response = await client.post(path, json=payload)
        else:
            response = await client.get(path)

        assert response.status_code == 401, f"Failed for {path}: expected 401, got {response.status_code}"
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_ivr_invalid_api_key_returns_403(client: AsyncClient):
    """Calling IVR endpoints with invalid X-API-Key must return 403 Forbidden."""
    headers = {"X-API-Key": "invalid-secret-key-attacker"}
    response = await client.post(
        "/api/ivr/call/start",
        json={"caller_phone": "9876543203"},
        headers=headers,
    )
    assert response.status_code == 403
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_ivr_valid_api_key_accepted(client: AsyncClient, seed_data: dict):
    """Calling IVR endpoints with valid X-API-Key must succeed."""
    headers = {"X-API-Key": settings.IVR_API_KEY}
    response = await client.post(
        "/api/ivr/call/start",
        json={"caller_phone": "9876543203", "language": "en"},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert "call_sid" in data
    assert "speak_text" in data
    assert data["gather_dtmf"] is True


@pytest.mark.asyncio
async def test_ivr_brute_force_pin_lockout_via_api(client: AsyncClient, seed_data: dict):
    """Verify that 3 consecutive wrong PINs lock the caller's account and terminate session."""
    headers = {"X-API-Key": settings.IVR_API_KEY}
    patient_phone = seed_data["users"]["patient"].phone  # 9876543203
    correct_pin = patient_phone[-4:]  # 3203

    # Start a call
    start_res = await client.post(
        "/api/ivr/call/start",
        json={"caller_phone": patient_phone},
        headers=headers,
    )
    assert start_res.status_code == 201
    call_sid = start_res.json()["call_sid"]

    # 1. Select English (2)
    step1 = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "2"},
        headers=headers,
    )
    assert step1.status_code == 200
    assert step1.json()["current_menu"] == "MAIN_MENU"

    # 2. Select Option 4 (Create Healthcare Request) -> requires PIN authentication
    step2 = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "4"},
        headers=headers,
    )
    assert step2.status_code == 200
    assert step2.json()["current_menu"] == "AUTH_PIN"

    # 3. Enter wrong PIN attempt 1
    step3 = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "0000"},
        headers=headers,
    )
    assert step3.status_code == 200
    assert step3.json()["is_verified"] is False
    assert step3.json()["hangup"] is False

    # 4. Enter wrong PIN attempt 2
    step4 = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "1111"},
        headers=headers,
    )
    assert step4.status_code == 200
    assert step4.json()["is_verified"] is False
    assert step4.json()["hangup"] is False

    # 5. Enter wrong PIN attempt 3 -> triggers 15-minute brute-force lockout and terminates session
    step5 = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "2222"},
        headers=headers,
    )
    assert step5.status_code == 200
    assert step5.json()["is_verified"] is False
    assert step5.json()["hangup"] is True
    assert "lock" in step5.json()["speak_text"].lower() or "பூட்டப்பட்டுள்ளது" in step5.json()["speak_text"]

    # 6. Start a new call for the same caller phone
    start_res2 = await client.post(
        "/api/ivr/call/start",
        json={"caller_phone": patient_phone},
        headers=headers,
    )
    assert start_res2.status_code == 201
    call_sid2 = start_res2.json()["call_sid"]

    # Select English (2)
    await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid2, "digits": "2"},
        headers=headers,
    )
    # Select Option 4 (Request) -> prompts for PIN
    await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid2, "digits": "4"},
        headers=headers,
    )
    # Enter the CORRECT PIN -> must be immediately rejected because of active lockout!
    lock_check = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid2, "digits": correct_pin},
        headers=headers,
    )
    assert lock_check.status_code == 200
    assert lock_check.json()["is_verified"] is False
    assert lock_check.json()["hangup"] is True


@pytest.mark.asyncio
async def test_ivr_session_isolation_and_not_found(client: AsyncClient):
    """Querying an unknown session ID must return 404."""
    headers = {"X-API-Key": settings.IVR_API_KEY}
    fake_id = str(uuid.uuid4())

    status_res = await client.get(f"/api/ivr/session/{fake_id}", headers=headers)
    assert status_res.status_code == 404
    assert status_res.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_ivr_dtmf_sanitization_and_sql_injection(client: AsyncClient, seed_data: dict):
    """Malicious input in DTMF digits must be safely handled without database or syntax errors."""
    headers = {"X-API-Key": settings.IVR_API_KEY}
    start_res = await client.post(
        "/api/ivr/call/start",
        json={"caller_phone": "9876543203"},
        headers=headers,
    )
    call_sid = start_res.json()["call_sid"]

    # Send SQL injection string as DTMF digits
    input_res = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "' OR '1'='1"},
        headers=headers,
    )
    assert input_res.status_code == 200
    # Should safely treat as invalid option without crashing
    data = input_res.json()
    assert data["call_sid"] == call_sid
    assert "speak_text" in data
