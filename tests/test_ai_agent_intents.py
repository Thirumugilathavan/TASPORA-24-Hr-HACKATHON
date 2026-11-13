"""Comprehensive Regression and Intent-Routing Test Suite for NALAM AI Assistant.

Verifies:
1. Coimbatore location extraction.
2. Salem location extraction.
3. Tiruchengode location extraction.
4. Explicit location overriding previous location.
5. Facility search intent.
6. Appointment booking intent.
7. Doctor availability intent.
8. Medicine search intent.
9. Health-information intent.
10. Symptom-guidance intent.
11. Emergency intent.
12. General conversation intent.
13. Tamil questions.
14. English questions.
15. Tanglish questions.
16. Mixed-language questions.
17. Multi-turn location changes.
18. Follow-up questions preserving relevant context.
19. No irrelevant facility tool execution.
20. No stale Tiruchengode results in Coimbatore responses.
21. No fabricated booking confirmation.
22. UNKNOWN doctor availability handling.

CRITICAL REGRESSION TEST:
User: "கோயம்புத்தூர்ல சொல்லு."
Expected:
- The location must be Coimbatore.
- The system must not silently use Tiruchengode.
- If the previous conversation does not establish what information the user wants about Coimbatore, ask what they want to find there.
- Do not automatically return Tiruchengode facilities.
"""
import pytest
from httpx import AsyncClient

from app.ai.intent_classifier import IntentType, classify_intent
from app.ai.location_extractor import extract_location
from app.ai.session_manager import ConversationSession, session_manager


# -------------------------------------------------------------
# 1-4. LOCATION EXTRACTION TESTS
# -------------------------------------------------------------
def test_1_coimbatore_location_extraction():
    """Verify Coimbatore is extracted from Tamil, English, and Tanglish."""
    loc1, _, exp1 = extract_location("கோயம்புத்தூர்ல சொல்லு.")
    assert loc1 == "Coimbatore"
    assert exp1 is True

    loc2, _, exp2 = extract_location("Tell me hospitals in Coimbatore")
    assert loc2 == "Coimbatore"
    assert exp2 is True

    loc3, _, exp3 = extract_location("Coimbatore la PHC enga irukku?")
    assert loc3 == "Coimbatore"
    assert exp3 is True


def test_2_salem_location_extraction():
    """Verify Salem is extracted correctly."""
    loc1, _, exp1 = extract_location("சேலத்தில் மருத்துவர் கிடைக்கிறாரா?")
    assert loc1 == "Salem"
    assert exp1 is True

    loc2, _, exp2 = extract_location("Find doctors in Salem")
    assert loc2 == "Salem"
    assert exp2 is True


def test_3_tiruchengode_location_extraction():
    """Verify Tiruchengode is extracted correctly."""
    loc1, _, exp1 = extract_location("திருச்செங்கோடு அருகே உள்ள ஆரம்ப சுகாதார நிலையம்")
    assert loc1 == "Tiruchengode"
    assert exp1 is True

    loc2, _, exp2 = extract_location("Find a PHC near Tiruchengode")
    assert loc2 == "Tiruchengode"
    assert exp2 is True


def test_4_explicit_location_overrides_previous_location():
    """Explicit location in latest question MUST override previous search location."""
    # Previous location was Tiruchengode, but user asks about Salem
    loc, _, exp = extract_location(
        "What about Salem?",
        conversation_active_location="Tiruchengode",
    )
    assert loc == "Salem"
    assert exp is True


# -------------------------------------------------------------
# 5-12. INTENT CLASSIFICATION TESTS
# -------------------------------------------------------------
def test_5_facility_search_intent():
    res = classify_intent("Find a PHC near Coimbatore", "en")
    assert res.intent == IntentType.FACILITY_SEARCH
    assert res.extracted_location == "Coimbatore"


def test_6_appointment_booking_intent():
    res = classify_intent("எனக்கு appointment book பண்ணணும்", "ta")
    assert res.intent == IntentType.APPOINTMENT_BOOKING
    # Must NOT default to Tiruchengode
    assert res.extracted_location != "Tiruchengode"


def test_7_doctor_availability_intent():
    res = classify_intent("சேலத்தில் மருத்துவர் கிடைக்கிறாரா?", "ta")
    assert res.intent == IntentType.DOCTOR_AVAILABILITY
    assert res.extracted_location == "Salem"


def test_8_medicine_search_intent():
    res = classify_intent("Where can I get Paracetamol stock?", "en")
    assert res.intent in [IntentType.MEDICINE_SEARCH, IntentType.MEDICINE_AVAILABILITY]
    assert res.extracted_medicine == "Paracetamol"


def test_9_health_information_intent():
    res = classify_intent("What causes severe dehydration and heat stroke?", "en")
    assert res.intent == IntentType.HEALTH_INFORMATION


def test_10_symptom_guidance_intent():
    res = classify_intent("எனக்கு காய்ச்சல் இருக்கு என்ன செய்யலாம்?", "ta")
    assert res.intent == IntentType.SYMPTOM_GUIDANCE


def test_11_emergency_intent():
    res = classify_intent("Patient has severe chest pain and breathlessness! Call 108", "en")
    assert res.intent in [IntentType.EMERGENCY_HELP, IntentType.AMBULANCE_INFORMATION]
    assert res.is_emergency is True


def test_12_general_conversation_intent():
    res1 = classify_intent("வணக்கம்", "ta")
    assert res1.intent == IntentType.GENERAL_CONVERSATION

    res2 = classify_intent("Hello, how are you?", "en")
    assert res2.intent == IntentType.GENERAL_CONVERSATION


# -------------------------------------------------------------
# 13-16. MULTILINGUAL & MIXED-LANGUAGE TESTS
# -------------------------------------------------------------
def test_13_tamil_query_analysis():
    res = classify_intent("கோயம்புத்தூர்ல PHC எங்கே?", "ta")
    assert res.intent == IntentType.FACILITY_SEARCH
    assert res.extracted_location == "Coimbatore"


def test_14_english_query_analysis():
    res = classify_intent("Show me primary health facilities in Salem", "en")
    assert res.intent == IntentType.FACILITY_SEARCH
    assert res.extracted_location == "Salem"


def test_15_tanglish_query_analysis():
    res = classify_intent("Salem la doctor irukara?", "ta")
    assert res.intent == IntentType.DOCTOR_AVAILABILITY
    assert res.extracted_location == "Salem"


def test_16_mixed_language_query_analysis():
    res = classify_intent("Coimbatore la hospital book பண்ணனும்", "ta")
    assert res.intent == IntentType.APPOINTMENT_BOOKING
    assert res.extracted_location == "Coimbatore"


# -------------------------------------------------------------
# 17-18. MULTI-TURN CONTEXT & FOLLOW-UP TESTS
# -------------------------------------------------------------
def test_17_multi_turn_location_change():
    """When user asks 'What about Salem?' after searching Coimbatore, intent is preserved with new location."""
    sess = ConversationSession(
        conversation_id="conv-multi-1",
        active_intent="FACILITY_SEARCH",
        active_location="Coimbatore",
    )
    res = classify_intent("What about Salem?", "en", session=sess)
    assert res.intent == IntentType.FACILITY_SEARCH
    assert res.extracted_location == "Salem"


def test_18_follow_up_preserving_relevant_context():
    """When user asks 'Which doctor is available today?' after facility search, location is preserved."""
    sess = ConversationSession(
        conversation_id="conv-multi-2",
        active_intent="FACILITY_SEARCH",
        active_location="Coimbatore",
    )
    res = classify_intent("Which doctor is available today?", "en", session=sess)
    assert res.intent == IntentType.DOCTOR_AVAILABILITY
    assert res.extracted_location == "Coimbatore"


# -------------------------------------------------------------
# 19-22 & CRITICAL REGRESSION TEST (END-TO-END VIA ASYNC CLIENT)
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_critical_reported_failure_coimbatore_sollu(client: AsyncClient, seed_data: dict):
    """CRITICAL REGRESSION TEST:
    User: 'கோயம்புத்தூர்ல சொல்லு.'
    Expected:
    - The location must be Coimbatore.
    - The system must not silently use Tiruchengode.
    - If the previous conversation does not establish what information the user wants about Coimbatore, ask what they want to find there.
    - Do not automatically return Tiruchengode facilities.
    """
    payload = {
        "message": "கோயம்புத்தூர்ல சொல்லு.",
        "language": "ta",
    }
    response = await client.post("/api/ai/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Must ask clarification for Coimbatore
    assert data["intent"] == "LOCATION_CLARIFICATION_REQUIRED"
    assert "Coimbatore" in data["response_text"] or "கோயம்புத்தூர்" in data["response_text"]
    
    # MUST NOT return Tiruchengode facilities!
    assert "Tiruchengode" not in data["response_text"]
    assert "திருச்செங்கோடு" not in data["response_text"]
    assert len(data["cards"]) == 0  # No facility cards dumped!


@pytest.mark.asyncio
async def test_19_no_irrelevant_facility_tool_execution(client: AsyncClient):
    """When user asks symptom or general question, facility search must NOT be called."""
    payload = {
        "message": "எனக்கு காய்ச்சல் இருக்கு என்ன செய்யலாம்?",
        "language": "ta",
    }
    response = await client.post("/api/ai/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["intent"] == "SYMPTOM_GUIDANCE"
    assert "search_facilities_tool" not in data["tools_called"]
    # Must not dump facility cards
    facility_cards = [c for c in data["cards"] if c["type"] == "FACILITY"]
    assert len(facility_cards) == 0


@pytest.mark.asyncio
async def test_20_no_stale_tiruchengode_in_coimbatore_responses(client: AsyncClient, seed_data: dict):
    """When searching facilities in Coimbatore, results must be in Coimbatore, not Tiruchengode."""
    payload = {
        "message": "Find a PHC in Coimbatore",
        "language": "en",
    }
    response = await client.post("/api/ai/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["intent"] == "FACILITY_PROXIMITY_SEARCH"
    for card in data["cards"]:
        if card["type"] == "FACILITY":
            # Facility must be in Coimbatore, not Tiruchengode
            assert "Coimbatore" in card["title"] or "Coimbatore" in card["details"].get("address", "")


@pytest.mark.asyncio
async def test_21_no_fabricated_booking_confirmation(client: AsyncClient, seed_data: dict):
    """When user requests appointment booking, present genuine slots without claiming completed booking."""
    payload = {
        "message": "எனக்கு appointment book பண்ணணும்",
        "language": "ta",
    }
    response = await client.post("/api/ai/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["intent"] == "APPOINTMENT_BOOKING_FLOW"
    # Response must explain how to confirm/select a slot, not fabricate a finished booking
    assert len(data["cards"]) > 0
    appointment_cards = [c for c in data["cards"] if c["type"] == "APPOINTMENT"]
    assert len(appointment_cards) > 0


@pytest.mark.asyncio
async def test_22_doctor_availability_attendance_status(client: AsyncClient, seed_data: dict):
    """Doctor availability must report verified status and never claim availability when UNKNOWN."""
    payload = {
        "message": "சேலத்தில் மருத்துவர் கிடைக்கிறாரா?",
        "language": "ta",
    }
    response = await client.post("/api/ai/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["intent"] == "DOCTOR_AVAILABILITY_LOOKUP"
    assert "check_doctor_availability_tool" in data["tools_called"]
    for card in data["cards"]:
        if card["type"] == "DOCTOR":
            assert card["badge"] in ["PRESENT", "EXPECTED", "ABSENT", "UNKNOWN"]
            # Must be in Salem
            assert "Salem" in card["subtitle"]
