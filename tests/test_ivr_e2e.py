from typing import Any, Dict
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.appointment import Appointment
from app.models.ivr import IVRSession
from app.models.request import HealthcareRequest
from app.schemas.shared import AppointmentStatus


@pytest.mark.asyncio
async def test_ivr_e2e_full_tamil_journey(client: AsyncClient, seed_data: Dict[str, Any], db_session: AsyncSession):
    """Full End-to-End caller journey in Tamil:

    Inbound call -> Tamil select -> PIN auth -> Request Creation ->
    AI Recommendation -> Appointment Booking -> Status Check ->
    Appointment Cancellation -> Safe Hangup.
    """
    headers = {"X-API-Key": settings.IVR_API_KEY}
    patient = seed_data["users"]["patient"]
    phone = patient.phone  # "9876543203"
    pin = phone[-4:]       # "3203"

    # Step 1: Inbound call initiation
    start_res = await client.post(
        "/api/ivr/call/start",
        json={"caller_phone": phone},
        headers=headers,
    )
    assert start_res.status_code == 201
    call_sid = start_res.json()["call_sid"]
    assert "CareBridge" in start_res.json()["speak_text"]

    # Step 2: Select Tamil (press 1)
    lang_res = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "1"},
        headers=headers,
    )
    assert lang_res.status_code == 200
    assert lang_res.json()["language"] == "ta"
    assert "முதன்மை மெனு" in lang_res.json()["speak_text"]

    # Step 3: Choose 4 (Create Healthcare Request) -> requires PIN
    req_menu = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "4"},
        headers=headers,
    )
    assert req_menu.status_code == 200
    assert req_menu.json()["current_menu"] == "AUTH_PIN"
    assert "பின் எண்" in req_menu.json()["speak_text"] or "பின்" in req_menu.json()["speak_text"]

    # Step 4: Submit 4-digit PIN ("3203")
    auth_res = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": pin},
        headers=headers,
    )
    assert auth_res.status_code == 200
    assert auth_res.json()["is_verified"] is True
    assert auth_res.json()["current_menu"] == "REQUEST_TYPE_SELECT"
    assert "மருத்துவ ஆலோசனை" in auth_res.json()["speak_text"]

    # Step 5: Select 1 (Consultation request)
    type_res = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "1"},
        headers=headers,
    )
    assert type_res.status_code == 200
    assert type_res.json()["current_menu"] == "REQUEST_URGENCY_SELECT"

    # Step 6: Select 1 (Normal Urgency) -> Request created, Recommendations offered
    urgency_res = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "1"},
        headers=headers,
    )
    assert urgency_res.status_code == 200
    assert urgency_res.json()["current_menu"] == "REQUEST_CONFIRMED"
    assert "பதிவு செய்யப்பட்டது" in urgency_res.json()["speak_text"]

    # Step 7: Press 1 to hear recommendations
    rec_res = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "1"},
        headers=headers,
    )
    assert rec_res.status_code == 200
    assert rec_res.json()["current_menu"] == "RECOMMENDATIONS"
    assert "பரிந்துரை" in rec_res.json()["speak_text"]

    # Step 8: Press 1 to book appointment at recommended facility
    slot_res = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "1"},
        headers=headers,
    )
    assert slot_res.status_code == 200
    assert slot_res.json()["current_menu"] == "APPOINTMENT_SLOT_SELECT"
    assert "நேரத்தை தேர்வு செய்யவும்" in slot_res.json()["speak_text"] or "10" in slot_res.json()["speak_text"]

    # Step 9: Select slot 1 (10:00 AM) -> Booked
    book_res = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "1"},
        headers=headers,
    )
    assert book_res.status_code == 200
    assert book_res.json()["current_menu"] == "MAIN_MENU"
    assert "முன்பதிவு உறுதி செய்யப்பட்டது" in book_res.json()["speak_text"]

    # Verify Appointment exists in DB
    appt_stmt = select(Appointment).where(Appointment.status == AppointmentStatus.BOOKED)
    appt_res = await db_session.execute(appt_stmt)
    appts = list(appt_res.scalars().all())
    assert len(appts) >= 1

    # Step 10: From Main Menu, select 5 (Check Status)
    status_res = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "5"},
        headers=headers,
    )
    assert status_res.status_code == 200
    assert status_res.json()["current_menu"] == "STATUS_MENU"
    assert "கோரிக்கை" in status_res.json()["speak_text"]
    assert "முன்பதிவு" in status_res.json()["speak_text"]

    # Step 11: Press 1 to cancel the latest appointment -> explicit confirmation prompt
    confirm_res = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "1"},
        headers=headers,
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["current_menu"] == "CANCEL_CONFIRM"
    assert "ரத்து செய்ய" in confirm_res.json()["speak_text"]

    # Step 12: Press 1 to confirm cancellation
    cancel_res = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "1"},
        headers=headers,
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["current_menu"] == "MAIN_MENU"
    assert "வெற்றிகரமாக ரத்து செய்யப்பட்டது" in cancel_res.json()["speak_text"]

    # Verify Appointment status in DB changed to CANCELLED
    await db_session.refresh(appts[0])
    assert appts[0].status == AppointmentStatus.CANCELLED

    # Step 13: Press 9 to end the call safely
    exit_res = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "9"},
        headers=headers,
    )
    assert exit_res.status_code == 200
    assert exit_res.json()["hangup"] is True
    assert exit_res.json()["session_status"] == "COMPLETED"
    assert "நன்றி" in exit_res.json()["speak_text"]


@pytest.mark.asyncio
async def test_ivr_e2e_full_english_journey(client: AsyncClient, seed_data: Dict[str, Any]):
    """Full End-to-End caller journey in English:

    Inbound call -> English select -> Facilities list -> Doctor check
    (strict PRESENT vs EXPECTED check) -> Medicine probabilistic stock check ->
    Emergency 108 guidance -> Menu repeat -> Safe Hangup.
    """
    headers = {"X-API-Key": settings.IVR_API_KEY}
    phone = "9876543203"

    # Step 1: Start call
    start_res = await client.post(
        "/api/ivr/call/start",
        json={"caller_phone": phone},
        headers=headers,
    )
    assert start_res.status_code == 201
    call_sid = start_res.json()["call_sid"]

    # Step 2: Select English (press 2)
    step1 = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "2"},
        headers=headers,
    )
    assert step1.status_code == 200
    assert step1.json()["language"] == "en"
    assert "Main Menu" in step1.json()["speak_text"]

    # Step 3: Check Nearby Facilities (press 1)
    step2 = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "1"},
        headers=headers,
    )
    assert step2.status_code == 200
    assert step2.json()["current_menu"] == "FACILITIES_LIST"
    assert "km" in step2.json()["speak_text"].lower() or "facilities" in step2.json()["speak_text"].lower()

    # Step 4: Return to Main Menu (press 0)
    step3 = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "0"},
        headers=headers,
    )
    assert step3.status_code == 200
    assert step3.json()["current_menu"] == "MAIN_MENU"

    # Step 5: Check Doctor Availability (press 2)
    step4 = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "2"},
        headers=headers,
    )
    assert step4.status_code == 200
    doc_text = step4.json()["speak_text"].lower()
    # Must clearly state EXPECTED attendance distinction
    assert "expected" in doc_text or "planned" in doc_text or "confirmed" in doc_text

    # Step 6: Return to Main Menu (press 0)
    step5 = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "0"},
        headers=headers,
    )
    assert step5.status_code == 200

    # Step 7: Check Medicine Stock (press 3)
    step6 = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "3"},
        headers=headers,
    )
    assert step6.status_code == 200
    assert step6.json()["current_menu"] == "MEDICINE_SELECT"

    # Step 8: Select medicine 1
    step7 = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "1"},
        headers=headers,
    )
    assert step7.status_code == 200
    med_text = step7.json()["speak_text"].lower()
    assert "percent" in med_text or "%" in med_text or "likely" in med_text or "uncertain" in med_text

    # Step 9: Emergency guidance (press 7)
    step8 = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "7"},
        headers=headers,
    )
    assert step8.status_code == 200
    assert "108" in step8.json()["speak_text"]

    # Step 10: Repeat menu (press 8)
    step9 = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "8"},
        headers=headers,
    )
    assert step9.status_code == 200
    assert "Main Menu" in step9.json()["speak_text"]

    # Step 11: End call safely (press 9)
    step10 = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "digits": "9"},
        headers=headers,
    )
    assert step10.status_code == 200
    assert step10.json()["hangup"] is True
    assert step10.json()["session_status"] == "COMPLETED"
    assert "Thank you" in step10.json()["speak_text"]
