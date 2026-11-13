"""Comprehensive Test Suite for Bilingual IVR Language Selection in NALAM AI.

Verifies all 17 required criteria from prompt:
1. New call plays bilingual language selection first.
2. Pressing 1 selects Tamil (ta).
3. Pressing 2 selects English (en).
4. Tamil welcome audio configuration (ta-IN, Nalini).
5. English welcome audio configuration (en-IN).
6. Tamil STT receives correct language.
7. English STT receives correct language.
8. AI responses respect explicit Tamil selection.
9. AI responses respect explicit English selection.
10. Language persists across multiple turns.
11. Invalid keypad input triggers another prompt.
12. No input triggers retry handling.
13. Repeated failures trigger documented fallback.
14. Concurrent callers retain separate language states.
15. Language switching preserves conversation history.
16. Existing telephony webhook authentication continues working.
17. Existing IVR functionality remains operational.
"""
import base64
import uuid
from typing import Any, Dict
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent import NalamAIAgent
from app.ai.gnani_adapter import gnani_adapter
from app.ai.schemas import AIChatRequest
from app.core.config import settings
from app.models.ivr import IVRSession
from app.schemas.ivr import IVRInputIn, IVRStartCallIn
from app.services.ivr_prompt_service import IVRPromptService
from app.services.ivr_service import IVRService
from tests.test_ivr_live_telephony import generate_twilio_signature


# -----------------------------------------------------------------------------
# 1. New call plays bilingual language selection first
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_bilingual_menu_plays_before_ai_conversation(client: AsyncClient):
    headers = {"X-API-Key": settings.IVR_API_KEY}
    call_sid = f"test-call-{uuid.uuid4().hex[:8]}"

    res = await client.post(
        "/api/ivr/call/start",
        json={"caller_phone": "9876500001", "call_sid": call_sid},
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()

    assert data["current_menu"] == "LANGUAGE_SELECT"
    assert data["gather_dtmf"] is True
    # Verify bilingual greeting text
    assert "வணக்கம்! நலம் மருத்துவ உதவி மையத்திற்கு உங்களை வரவேற்கிறோம்" in data["speak_text"]
    assert "தமிழில் தொடர 1-ஐ அழுத்தவும்" in data["speak_text"]
    assert "Welcome to NALAM" in data["speak_text"]
    assert "Press 1 to continue in Tamil" in data["speak_text"]
    assert "Press 2 to continue in English" in data["speak_text"]


# -----------------------------------------------------------------------------
# 2. Pressing 1 selects Tamil (ta)
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_pressing_1_selects_tamil(client: AsyncClient, db_session: AsyncSession):
    headers = {"X-API-Key": settings.IVR_API_KEY}
    call_sid = f"test-call-{uuid.uuid4().hex[:8]}"

    await client.post("/api/ivr/call/start", json={"caller_phone": "9876500001", "call_sid": call_sid}, headers=headers)
    res = await client.post("/api/ivr/call/input", json={"call_sid": call_sid, "digits": "1"}, headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "ta"
    assert data["current_menu"] == "MAIN_MENU"
    assert "வணக்கம்! நான் நலம் AI உதவியாளர்" in data["speak_text"]
    assert "முதன்மை மெனு" in data["speak_text"]

    # Verify database session state
    stmt = select(IVRSession).where(IVRSession.call_sid == call_sid)
    sess = (await db_session.execute(stmt)).scalar_one()
    assert sess.language == "ta"
    assert sess.menu_state.get("selected_language") == "ta"
    assert sess.menu_state.get("language_confirmed") is True
    assert sess.menu_state.get("is_fallback_language") is False


# -----------------------------------------------------------------------------
# 3. Pressing 2 selects English (en)
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_pressing_2_selects_english(client: AsyncClient, db_session: AsyncSession):
    headers = {"X-API-Key": settings.IVR_API_KEY}
    call_sid = f"test-call-{uuid.uuid4().hex[:8]}"

    await client.post("/api/ivr/call/start", json={"caller_phone": "9876500002", "call_sid": call_sid}, headers=headers)
    res = await client.post("/api/ivr/call/input", json={"call_sid": call_sid, "digits": "2"}, headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "en"
    assert data["current_menu"] == "MAIN_MENU"
    assert "Hello! I am your NALAM healthcare assistant" in data["speak_text"]
    assert "Main Menu" in data["speak_text"]

    # Verify database session state
    stmt = select(IVRSession).where(IVRSession.call_sid == call_sid)
    sess = (await db_session.execute(stmt)).scalar_one()
    assert sess.language == "en"
    assert sess.menu_state.get("selected_language") == "en"
    assert sess.menu_state.get("language_confirmed") is True
    assert sess.menu_state.get("is_fallback_language") is False


# -----------------------------------------------------------------------------
# 4. Tamil welcome audio configuration
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_tamil_welcome_audio_configuration():
    tamil_welcome = IVRPromptService.get_language_welcome_message("ta")
    tts_res = await gnani_adapter.synthesize(text=tamil_welcome, language="ta")

    assert tts_res["status"] == "success"
    assert tts_res["language"] == "ta"
    assert tts_res["indic_language"] == "ta-IN"
    assert tts_res["voice"] == "Nalini"
    assert len(tts_res["audio_base64"]) > 0


# -----------------------------------------------------------------------------
# 5. English welcome audio configuration
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_english_welcome_audio_configuration():
    english_welcome = IVRPromptService.get_language_welcome_message("en")
    tts_res = await gnani_adapter.synthesize(text=english_welcome, language="en")

    assert tts_res["status"] == "success"
    assert tts_res["language"] == "en"
    assert tts_res["indic_language"] == "en-IN"
    assert tts_res["voice"] == "en-IN-Standard-A"
    assert len(tts_res["audio_base64"]) > 0


# -----------------------------------------------------------------------------
# 6. Tamil STT receives correct language
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_tamil_stt_receives_correct_language():
    sample_audio_b64 = base64.b64encode(b"RIFFdummywavdata").decode("ascii")
    stt_res = await gnani_adapter.transcribe(audio_base64=sample_audio_b64, language="ta")

    assert stt_res["language"] == "ta"
    assert stt_res["indic_language"] == "ta-IN"
    assert stt_res["detected_language"] == "ta"
    assert "திருச்செங்கோடு" in stt_res["transcribed_text"]


# -----------------------------------------------------------------------------
# 7. English STT receives correct language
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_english_stt_receives_correct_language():
    sample_audio_b64 = base64.b64encode(b"RIFFdummywavdata").decode("ascii")
    stt_res = await gnani_adapter.transcribe(audio_base64=sample_audio_b64, language="en")

    assert stt_res["language"] == "en"
    assert stt_res["indic_language"] == "en-IN"
    assert stt_res["detected_language"] == "en"
    assert "Tiruchengode" in stt_res["transcribed_text"]


# -----------------------------------------------------------------------------
# 8. AI responses respect explicit Tamil selection
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_ai_responses_respect_tamil_selection(client: AsyncClient, seed_data: dict, db_session: AsyncSession):
    agent = NalamAIAgent()
    req = AIChatRequest(
        message="அருகிலுள்ள ஆரம்ப சுகாதார நிலையத்தை கண்டுபிடி",
        language="ta",
        location_context="Tiruchengode",
    )
    resp = await agent.execute_turn(req, db_session)

    assert resp.language == "ta"
    # Response must be in Tamil and contain real facility cards
    assert len(resp.cards) > 0
    assert any("ஆரம்ப சுகாதார நிலையம்" in c.subtitle or "PHC" in c.subtitle for c in resp.cards)
    assert "மருத்துவமனை" in resp.response_text or "ஆரம்ப சுகாதார" in resp.response_text or "நிலையங்கள்" in resp.response_text


# -----------------------------------------------------------------------------
# 9. AI responses respect explicit English selection
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_ai_responses_respect_english_selection(client: AsyncClient, seed_data: dict, db_session: AsyncSession):
    agent = NalamAIAgent()
    req = AIChatRequest(
        message="Find nearby primary healthcare centres",
        language="en",
        location_context="Tiruchengode",
    )
    resp = await agent.execute_turn(req, db_session)

    assert resp.language == "en"
    assert len(resp.cards) > 0
    assert "facilities" in resp.response_text.lower() or "phc" in resp.response_text.lower()


# -----------------------------------------------------------------------------
# 10. Language persists across multiple turns
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_language_persists_across_multiple_turns(client: AsyncClient):
    headers = {"X-API-Key": settings.IVR_API_KEY}
    call_sid = f"test-call-{uuid.uuid4().hex[:8]}"

    # Turn 1: Start call
    await client.post("/api/ivr/call/start", json={"caller_phone": "9876500003", "call_sid": call_sid}, headers=headers)

    # Turn 2: Select Tamil (1)
    res_lang = await client.post("/api/ivr/call/input", json={"call_sid": call_sid, "digits": "1"}, headers=headers)
    assert res_lang.json()["language"] == "ta"

    # Turn 3: Press 1 (Facilities) -> language remains Tamil
    res_fac = await client.post("/api/ivr/call/input", json={"call_sid": call_sid, "digits": "1"}, headers=headers)
    assert res_fac.json()["language"] == "ta"
    assert "மருத்துவமனை" in res_fac.json()["speak_text"]

    # Turn 4: Press 8 (Repeat current menu) -> language remains Tamil
    res_rep = await client.post("/api/ivr/call/input", json={"call_sid": call_sid, "digits": "8"}, headers=headers)
    assert res_rep.json()["language"] == "ta"
    assert "மருத்துவமனை" in res_rep.json()["speak_text"]


# -----------------------------------------------------------------------------
# 11. Invalid input triggers another prompt
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_invalid_input_triggers_another_prompt(client: AsyncClient, db_session: AsyncSession):
    headers = {"X-API-Key": settings.IVR_API_KEY}
    call_sid = f"test-call-{uuid.uuid4().hex[:8]}"

    await client.post("/api/ivr/call/start", json={"caller_phone": "9876500004", "call_sid": call_sid}, headers=headers)

    # Send invalid digit '5'
    res = await client.post("/api/ivr/call/input", json={"call_sid": call_sid, "digits": "5"}, headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["current_menu"] == "LANGUAGE_SELECT"
    assert "தவறான தேர்வு" in data["speak_text"]
    assert "Invalid selection" in data["speak_text"]
    assert "Press 1 to continue in Tamil" in data["speak_text"]
    assert "Press 2 to continue in English" in data["speak_text"]

    # Verify retry count incremented
    stmt = select(IVRSession).where(IVRSession.call_sid == call_sid)
    sess = (await db_session.execute(stmt)).scalar_one()
    assert sess.retry_count == 1


# -----------------------------------------------------------------------------
# 12. No input triggers retry handling
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_no_input_triggers_retry_handling(client: AsyncClient, db_session: AsyncSession):
    headers = {"X-API-Key": settings.IVR_API_KEY}
    call_sid = f"test-call-{uuid.uuid4().hex[:8]}"

    await client.post("/api/ivr/call/start", json={"caller_phone": "9876500005", "call_sid": call_sid}, headers=headers)

    # Send empty digits (timeout)
    res = await client.post("/api/ivr/call/input", json={"call_sid": call_sid, "digits": ""}, headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["current_menu"] == "LANGUAGE_SELECT"
    assert "எந்த உள்ளீடும் பெறப்படவில்லை" in data["speak_text"]
    assert "No input detected" in data["speak_text"]

    # Verify retry count incremented
    stmt = select(IVRSession).where(IVRSession.call_sid == call_sid)
    sess = (await db_session.execute(stmt)).scalar_one()
    assert sess.retry_count == 1


# -----------------------------------------------------------------------------
# 13. Repeated failures trigger documented fallback
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_repeated_failures_trigger_documented_fallback(client: AsyncClient, db_session: AsyncSession):
    headers = {"X-API-Key": settings.IVR_API_KEY}
    call_sid = f"test-call-{uuid.uuid4().hex[:8]}"

    await client.post("/api/ivr/call/start", json={"caller_phone": "9876500006", "call_sid": call_sid}, headers=headers)

    # Attempt 1 (invalid digit 3)
    res1 = await client.post("/api/ivr/call/input", json={"call_sid": call_sid, "digits": "3"}, headers=headers)
    assert res1.json()["current_menu"] == "LANGUAGE_SELECT"

    # Attempt 2 (invalid digit 4)
    res2 = await client.post("/api/ivr/call/input", json={"call_sid": call_sid, "digits": "4"}, headers=headers)
    assert res2.json()["current_menu"] == "LANGUAGE_SELECT"

    # Attempt 3 (invalid digit 5 -> exhausts 3 retries, triggers documented fallback)
    res3 = await client.post("/api/ivr/call/input", json={"call_sid": call_sid, "digits": "5"}, headers=headers)
    assert res3.status_code == 200
    data = res3.json()

    assert data["current_menu"] == "MAIN_MENU"
    assert data["language"] == "ta"
    assert "அதிகபட்ச முயற்சிகள் முடிவடைந்தன" in data["speak_text"]
    assert "நலம் உதவி மையம் தானாகவே தமிழில் தொடர்கிறது" in data["speak_text"]

    # Verify session recorded as fallback without misclassifying caller choice
    stmt = select(IVRSession).where(IVRSession.call_sid == call_sid)
    sess = (await db_session.execute(stmt)).scalar_one()
    assert sess.language == "ta"
    assert sess.menu_state.get("is_fallback_language") is True
    assert sess.menu_state.get("language_confirmed") is False
    assert sess.menu_state.get("fallback_reason") == "MAX_RETRIES_EXCEEDED"


# -----------------------------------------------------------------------------
# 14. Concurrent callers retain separate language states
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_concurrent_callers_retain_separate_language_states(client: AsyncClient, db_session: AsyncSession):
    headers = {"X-API-Key": settings.IVR_API_KEY}
    call_sid_1 = f"test-caller-ta-{uuid.uuid4().hex[:8]}"
    call_sid_2 = f"test-caller-en-{uuid.uuid4().hex[:8]}"

    # Caller 1 starts and picks Tamil
    await client.post("/api/ivr/call/start", json={"caller_phone": "9876500011", "call_sid": call_sid_1}, headers=headers)
    await client.post("/api/ivr/call/input", json={"call_sid": call_sid_1, "digits": "1"}, headers=headers)

    # Caller 2 starts and picks English
    await client.post("/api/ivr/call/start", json={"caller_phone": "9876500022", "call_sid": call_sid_2}, headers=headers)
    await client.post("/api/ivr/call/input", json={"call_sid": call_sid_2, "digits": "2"}, headers=headers)

    # Verify Caller 1 session is Tamil
    stmt1 = select(IVRSession).where(IVRSession.call_sid == call_sid_1)
    sess1 = (await db_session.execute(stmt1)).scalar_one()
    assert sess1.language == "ta"

    # Verify Caller 2 session is English
    stmt2 = select(IVRSession).where(IVRSession.call_sid == call_sid_2)
    sess2 = (await db_session.execute(stmt2)).scalar_one()
    assert sess2.language == "en"

    # Caller 1 queries facilities -> gets Tamil
    res1 = await client.post("/api/ivr/call/input", json={"call_sid": call_sid_1, "digits": "1"}, headers=headers)
    assert res1.json()["language"] == "ta"
    assert "மருத்துவமனை" in res1.json()["speak_text"]

    # Caller 2 queries facilities -> gets English
    res2 = await client.post("/api/ivr/call/input", json={"call_sid": call_sid_2, "digits": "1"}, headers=headers)
    assert res2.json()["language"] == "en"
    assert "facilities" in res2.json()["speak_text"].lower()


# -----------------------------------------------------------------------------
# 15. Language switching preserves conversation history
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_language_switching_preserves_conversation_history(client: AsyncClient, db_session: AsyncSession):
    headers = {"X-API-Key": settings.IVR_API_KEY}
    call_sid = f"test-call-{uuid.uuid4().hex[:8]}"

    # Start and select Tamil
    await client.post("/api/ivr/call/start", json={"caller_phone": "9876500033", "call_sid": call_sid}, headers=headers)
    await client.post("/api/ivr/call/input", json={"call_sid": call_sid, "digits": "1"}, headers=headers)

    # Request language switch via spoken intent "Change language"
    res_switch = await client.post(
        "/api/ivr/call/input",
        json={"call_sid": call_sid, "speech_text": "Change language"},
        headers=headers,
    )
    assert res_switch.status_code == 200
    assert res_switch.json()["current_menu"] == "LANGUAGE_SELECT"
    assert "மொழியை மாற்ற" in res_switch.json()["speak_text"]
    assert "To change language" in res_switch.json()["speak_text"]

    # Select English (2)
    res_en = await client.post("/api/ivr/call/input", json={"call_sid": call_sid, "digits": "2"}, headers=headers)
    assert res_en.status_code == 200
    assert res_en.json()["language"] == "en"
    assert "Hello! I am your NALAM healthcare assistant" in res_en.json()["speak_text"]

    # Verify session has interaction audit trail preserved in database
    from app.models.ivr import IVRInteraction
    from sqlalchemy import func
    stmt = select(IVRSession).where(IVRSession.call_sid == call_sid)
    sess = (await db_session.execute(stmt)).scalar_one()
    interaction_count = (await db_session.execute(
        select(func.count(IVRInteraction.id)).where(IVRInteraction.session_id == sess.id)
    )).scalar_one()
    assert interaction_count >= 3
    assert sess.language == "en"


# -----------------------------------------------------------------------------
# 16. Existing webhook authentication remains intact
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_existing_webhook_authentication_remains_intact(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "TELEPHONY_PROVIDER", "twilio")
    monkeypatch.setattr(settings, "TELEPHONY_AUTH_TOKEN", "prod_secret_auth_token_888")
    monkeypatch.setattr(settings, "TELEPHONY_WEBHOOK_BASE_URL", "https://carebridge.org")

    # Inbound webhook without signature must be rejected with 403
    res = await client.post(
        "/api/ivr/webhooks/incoming",
        data={"CallSid": "CA_auth_check_999", "From": "+919876543201"},
    )
    assert res.status_code == 403

    # With valid signature, must succeed and present bilingual selection
    url = "https://carebridge.org/api/ivr/webhooks/incoming"
    params = {"CallSid": "CA_auth_check_999", "From": "+919876543201"}
    valid_sig = generate_twilio_signature(url, params, "prod_secret_auth_token_888")

    res_valid = await client.post(
        "/api/ivr/webhooks/incoming",
        data=params,
        headers={"X-Twilio-Signature": valid_sig},
    )
    assert res_valid.status_code == 200
    assert "application/xml" in res_valid.headers["content-type"]
    assert "NALAM" in res_valid.text
    assert "<Gather" in res_valid.text


# -----------------------------------------------------------------------------
# 17. Existing IVR functionality remains operational
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_existing_ivr_functionality_remains_operational(client: AsyncClient):
    headers = {"X-API-Key": settings.IVR_API_KEY}
    call_sid = f"test-call-{uuid.uuid4().hex[:8]}"

    # Start and select Tamil
    await client.post("/api/ivr/call/start", json={"caller_phone": "9876500055", "call_sid": call_sid}, headers=headers)
    await client.post("/api/ivr/call/input", json={"call_sid": call_sid, "digits": "1"}, headers=headers)

    # 1. Nearby facilities (Option 1)
    res_fac = await client.post("/api/ivr/call/input", json={"call_sid": call_sid, "digits": "1"}, headers=headers)
    assert res_fac.status_code == 200
    assert "மருத்துவமனை" in res_fac.json()["speak_text"]

    # 2. Return to Main Menu (Option 0)
    res_main = await client.post("/api/ivr/call/input", json={"call_sid": call_sid, "digits": "0"}, headers=headers)
    assert res_main.status_code == 200
    assert res_main.json()["current_menu"] == "MAIN_MENU"

    # 3. Emergency 108 guidance (Option 7)
    res_emg = await client.post("/api/ivr/call/input", json={"call_sid": call_sid, "digits": "7"}, headers=headers)
    assert res_emg.status_code == 200
    assert "108" in res_emg.json()["speak_text"]

    # 4. Safe hangup (Option 9)
    res_end = await client.post("/api/ivr/call/input", json={"call_sid": call_sid, "digits": "9"}, headers=headers)
    assert res_end.status_code == 200
    assert res_end.json()["hangup"] is True
    assert res_end.json()["session_status"] == "COMPLETED"
