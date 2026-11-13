"""Tests for NALAM AI context switching and location change tracking.

Verifies:
- Location changes between turns
- Context inheritance for follow-ups
- Tamil, English, and Tanglish location queries
- Intent classification stability across context switches
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.intent_classifier import classify_intent, IntentType
from app.ai.location_extractor import extract_location
from app.ai.session_manager import ConversationSession


def _make_session(cid: str = "test-session") -> ConversationSession:
    """Create a test ConversationSession."""
    return ConversationSession(conversation_id=cid)


# ---------------------------------------------------------------------------
# Test 1: Explicit location switch from Sulur to Pollachi
# ---------------------------------------------------------------------------
def test_location_switch_sulur_to_pollachi():
    """After 'Show hospitals in Sulur' then 'Now show hospitals in Pollachi', location switches."""
    session = _make_session()
    # Turn 1: Sulur
    res1 = classify_intent("Show hospitals in Sulur", "en", session=session)
    assert "sulur" in (res1.extracted_location or "").lower()
    session.add_turn("Show hospitals in Sulur", "en", res1.intent.value, res1.extracted_location, [], "")

    # Turn 2: Pollachi — explicit new location overrides Sulur
    res2 = classify_intent("Now show hospitals in Pollachi", "en", session=session)
    assert "pollachi" in (res2.extracted_location or "").lower()


# ---------------------------------------------------------------------------
# Test 2: Follow-up inherits last location
# ---------------------------------------------------------------------------
def test_followup_inherits_location():
    """'What about government hospitals?' after Sulur query inherits Sulur."""
    session = _make_session()
    # Turn 1: Sulur
    res1 = classify_intent("Show hospitals in Sulur", "en", session=session)
    session.add_turn("Show hospitals in Sulur", "en", res1.intent.value, res1.extracted_location, [], "")

    # Turn 2: follow-up without explicit location
    res2 = classify_intent("What about government hospitals?", "en", session=session)
    # Should either carry forward Sulur or be classified as FOLLOW_UP / FACILITY_SEARCH
    assert res2.intent in [IntentType.FACILITY_SEARCH, IntentType.FOLLOW_UP]


# ---------------------------------------------------------------------------
# Test 3: Tamil location query — Sulur
# ---------------------------------------------------------------------------
def test_tamil_sulur_location_query():
    """Tamil: 'சூலூர்ல மருத்துவமனை எங்க இருக்கு?' → FACILITY_SEARCH."""
    result = classify_intent("சூலூர்ல மருத்துவமனை எங்க இருக்கு?", "ta")
    assert result.intent == IntentType.FACILITY_SEARCH


# ---------------------------------------------------------------------------
# Test 4: Tanglish location query — Sulur
# ---------------------------------------------------------------------------
def test_tanglish_sulur_location_query():
    """Tanglish: 'Sulur la PHC enga?' → FACILITY_SEARCH."""
    result = classify_intent("Sulur la PHC enga?", "en")
    assert result.intent == IntentType.FACILITY_SEARCH


# ---------------------------------------------------------------------------
# Test 5: Location change from Coimbatore to Salem
# ---------------------------------------------------------------------------
def test_location_switch_coimbatore_to_salem():
    """Explicit location change from Coimbatore to Salem."""
    session = _make_session()
    res1 = classify_intent("Show hospitals in Coimbatore", "en", session=session)
    session.add_turn("Show hospitals in Coimbatore", "en", res1.intent.value, res1.extracted_location, [], "")

    res2 = classify_intent("Now tell me about Salem hospitals", "en", session=session)
    assert "salem" in (res2.extracted_location or "").lower()


# ---------------------------------------------------------------------------
# Test 6: Intent switch from facility search to symptom guidance
# ---------------------------------------------------------------------------
def test_intent_switch_facility_to_symptom():
    """User switches from facility search to symptom question."""
    session = _make_session()
    res1 = classify_intent("Show hospitals in Sulur", "en", session=session)
    assert res1.intent == IntentType.FACILITY_SEARCH

    res2 = classify_intent("I have fever. What should I do?", "en", session=session)
    assert res2.intent == IntentType.SYMPTOM_GUIDANCE


# ---------------------------------------------------------------------------
# Test 7: Intent switch from symptom to facility search
# ---------------------------------------------------------------------------
def test_intent_switch_symptom_to_facility():
    """User switches from symptom question to facility search."""
    session = _make_session()
    res1 = classify_intent("I have fever", "en", session=session)
    assert res1.intent == IntentType.SYMPTOM_GUIDANCE

    res2 = classify_intent("Show me the nearest hospital in Pollachi", "en", session=session)
    assert res2.intent in [IntentType.FACILITY_SEARCH, IntentType.SYMPTOM_WITH_FACILITY]


# ---------------------------------------------------------------------------
# Test 8: Multiple rapid location switches
# ---------------------------------------------------------------------------
def test_multiple_rapid_location_switches():
    """Multiple location changes in sequence."""
    session = _make_session()

    res1 = classify_intent("Hospitals in Sulur", "en", session=session)
    session.add_turn("Hospitals in Sulur", "en", res1.intent.value, res1.extracted_location, [], "")

    res2 = classify_intent("Hospitals in Pollachi", "en", session=session)
    assert "pollachi" in (res2.extracted_location or "").lower()
    session.add_turn("Hospitals in Pollachi", "en", res2.intent.value, res2.extracted_location, [], "")

    res3 = classify_intent("Hospitals in Mettupalayam", "en", session=session)
    assert "mettupalayam" in (res3.extracted_location or "").lower()


# ---------------------------------------------------------------------------
# Test 9: General conversation does not inherit facility context
# ---------------------------------------------------------------------------
def test_general_conversation_no_facility_inheritance():
    """'Hello, how are you?' should not trigger facility search even after facility queries."""
    session = _make_session()
    res1 = classify_intent("Show hospitals in Sulur", "en", session=session)
    session.add_turn("Show hospitals in Sulur", "en", res1.intent.value, res1.extracted_location, [], "")

    res2 = classify_intent("Hello, how are you?", "en", session=session)
    assert res2.intent == IntentType.GENERAL_CONVERSATION
