from datetime import datetime, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.telephony.mock_provider import MockTelephonyProvider
from app.integrations.telephony.twilio_provider import TwilioTelephonyProvider
from app.models.patient import Patient
from app.models.user import User
from app.schemas.ivr import IVRResponse, TelephonyEventType
from app.schemas.shared import AttendanceStatus, AvailabilityLabel
from app.services.ivr_auth_service import IVRAuthService, normalize_phone_number
from app.services.ivr_prompt_service import IVRPromptService


def test_phone_number_normalization():
    """Verify robust normalization of Indian phone numbers."""
    assert normalize_phone_number("9876543210") == "9876543210"
    assert normalize_phone_number("+919876543210") == "9876543210"
    assert normalize_phone_number("+91 98765-43210") == "9876543210"
    assert normalize_phone_number("09876543210") == "9876543210"
    assert normalize_phone_number("919876543210") == "9876543210"
    assert normalize_phone_number("(+91) 98765 43210") == "9876543210"
    assert normalize_phone_number("") == ""


def test_prompt_service_tamil_and_english():
    """Verify prompt service produces culturally appropriate Tamil and English audio text."""
    prompts = IVRPromptService()

    # Welcome
    welcome = prompts.get_welcome_prompt()
    assert "CareBridge" in welcome
    assert "1" in welcome
    assert "2" in welcome

    # Main menu
    menu_ta = prompts.get_main_menu("ta")
    assert "மருத்துவமனை" in menu_ta
    assert "மருந்து இருப்பு" in menu_ta

    menu_en = prompts.get_main_menu("en")
    assert "facilities" in menu_en.lower()
    assert "medicine" in menu_en.lower()

    # Doctor status: strict distinction between PRESENT and EXPECTED
    doc_pres_ta = prompts.get_doctor_status_prompt("Dr. Raman", "PHC Rampur", AttendanceStatus.PRESENT, "இன்று", "ta")
    assert "உறுதி செய்யப்பட்டுள்ளது" in doc_pres_ta

    doc_exp_ta = prompts.get_doctor_status_prompt("Dr. Raman", "PHC Rampur", AttendanceStatus.EXPECTED, "இன்று", "ta")
    assert "பணி அட்டவணையில் உள்ளார்" in doc_exp_ta
    assert "உறுதி செய்யப்படவில்லை" in doc_exp_ta

    doc_exp_en = prompts.get_doctor_status_prompt("Dr. Raman", "PHC Rampur", AttendanceStatus.EXPECTED, "today", "en")
    assert "EXPECTED" in doc_exp_en
    assert "not confirmed" in doc_exp_en.lower()

    # Medicine stock labels
    med_likely_ta = prompts.get_medicine_stock_result("Paracetamol", "PHC Rampur", AvailabilityLabel.LIKELY, 0.85, 0.70, "ta")
    assert "அதிக வாய்ப்புள்ளது" in med_likely_ta
    assert "மருத்துவ பரிந்துரை அல்ல" in med_likely_ta  # safety notice

    # Emergency guidance
    emg_ta = prompts.get_emergency_message("ta")
    assert "108" in emg_ta


@pytest.mark.asyncio
async def test_auth_service_pin_verification_and_lockout(db_session: AsyncSession, seed_data: dict):
    """Verify secure PIN verification, attempt rate-limiting, and 15-minute brute-force lockout."""
    auth = IVRAuthService(db_session)
    patient_user = seed_data["users"]["patient"]
    phone = patient_user.phone  # e.g. "9876543203"
    correct_pin = phone[-4:]    # default pin: "3203"

    # 1. Invalid PIN attempt 1
    valid, err = await auth.verify_pin(phone, "0000")
    assert valid is False
    assert err == "INVALID_PIN"

    # 2. Invalid PIN attempt 2
    valid, err = await auth.verify_pin(phone, "1111")
    assert valid is False
    assert err == "INVALID_PIN"

    # 3. Invalid PIN attempt 3 -> triggers lockout
    valid, err = await auth.verify_pin(phone, "2222")
    assert valid is False
    assert err == "LOCKED"

    # 4. Immediate attempt with CORRECT PIN while locked -> rejected as LOCKED
    valid, err = await auth.verify_pin(phone, correct_pin)
    assert valid is False
    assert err == "LOCKED"


@pytest.mark.asyncio
async def test_auth_service_successful_pin(db_session: AsyncSession, seed_data: dict):
    """Verify correct PIN succeeds and resets attempt counters."""
    auth = IVRAuthService(db_session)
    staff_user = seed_data["users"]["staff"]
    phone = staff_user.phone
    correct_pin = phone[-4:]

    valid, err = await auth.verify_pin(phone, correct_pin)
    assert valid is True
    assert err is None


def test_mock_telephony_provider():
    """Verify mock telephony provider formats JSON responses correctly."""
    provider = MockTelephonyProvider()
    event = provider.parse_webhook({"call_sid": "test-sid-1", "caller_phone": "9876500001", "digits": "1"}, {})
    assert event.call_sid == "test-sid-1"
    assert event.digits == "1"
    assert event.event_type == TelephonyEventType.GATHER

    resp = IVRResponse(
        call_sid="test-sid-1",
        speak_text="Test prompt",
        gather_dtmf=True,
    )
    formatted = provider.format_response(resp)
    assert isinstance(formatted, dict)
    assert formatted["call_sid"] == "test-sid-1"
    assert formatted["speak_text"] == "Test prompt"


def test_twilio_telephony_provider():
    """Verify Twilio adapter produces valid TwiML XML."""
    provider = TwilioTelephonyProvider()
    event = provider.parse_webhook({"CallSid": "CA123456", "From": "+919876500001", "Digits": "2"}, {})
    assert event.call_sid == "CA123456"
    assert event.digits == "2"

    resp = IVRResponse(
        call_sid="CA123456",
        speak_text="Welcome to CareBridge",
        language="ta",
        gather_dtmf=True,
        num_digits=1,
    )
    twiml = provider.format_response(resp)
    assert isinstance(twiml, str)
    assert "<?xml" in twiml
    assert "<Response>" in twiml
    assert "<Gather" in twiml
    assert "language=\"ta-IN\"" in twiml
    assert "Welcome to CareBridge" in twiml
