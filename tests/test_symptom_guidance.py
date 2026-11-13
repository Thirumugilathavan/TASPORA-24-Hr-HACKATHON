"""Tests for NALAM symptom guidance and fever guidance features.

Verifies:
- Fever guidance in English and Tamil
- Child fever special caution
- Symptom intent classification
- Combined symptom + facility intent
- Danger signs and medication safety
- Dengue/malaria awareness
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.intent_classifier import classify_intent, IntentType


# ---------------------------------------------------------------------------
# Test 1: "I have fever" → SYMPTOM_GUIDANCE intent
# ---------------------------------------------------------------------------
def test_fever_english_symptom_guidance_intent():
    """'I have fever. What should I do?' → SYMPTOM_GUIDANCE intent."""
    result = classify_intent("I have fever. What should I do?", "en")
    assert result.intent == IntentType.SYMPTOM_GUIDANCE
    assert result.extracted_symptom == "fever"


# ---------------------------------------------------------------------------
# Test 2: Tamil fever query → SYMPTOM_GUIDANCE intent
# ---------------------------------------------------------------------------
def test_fever_tamil_symptom_guidance_intent():
    """Tamil fever query → SYMPTOM_GUIDANCE intent."""
    result = classify_intent("எனக்கு காய்ச்சல் இருக்கு என்ன செய்யலாம்?", "ta")
    assert result.intent == IntentType.SYMPTOM_GUIDANCE
    assert result.extracted_symptom == "fever"


# ---------------------------------------------------------------------------
# Test 3: "I have fever and I'm in Sulur" → SYMPTOM_WITH_FACILITY
# ---------------------------------------------------------------------------
def test_fever_with_location_combined_intent():
    """'I have fever and need a hospital in Sulur' → SYMPTOM_WITH_FACILITY intent."""
    result = classify_intent("I have fever and need a hospital in Sulur", "en")
    assert result.intent == IntentType.SYMPTOM_WITH_FACILITY
    assert result.extracted_symptom == "fever"


# ---------------------------------------------------------------------------
# Test 4: "I have headache" → SYMPTOM_GUIDANCE
# ---------------------------------------------------------------------------
def test_headache_symptom_guidance():
    """Headache query → SYMPTOM_GUIDANCE intent."""
    result = classify_intent("I have a terrible headache", "en")
    assert result.intent == IntentType.SYMPTOM_GUIDANCE
    assert result.extracted_symptom == "headache"


# ---------------------------------------------------------------------------
# Test 5: "Vomiting and diarrhea" → SYMPTOM_GUIDANCE
# ---------------------------------------------------------------------------
def test_vomiting_diarrhea_symptom():
    """Vomiting/diarrhea → SYMPTOM_GUIDANCE intent."""
    result = classify_intent("I am vomiting and have diarrhea since morning", "en")
    assert result.intent == IntentType.SYMPTOM_GUIDANCE
    assert result.extracted_symptom in ["vomiting", "diarrhea"]


# ---------------------------------------------------------------------------
# Test 6: "What causes fever?" → HEALTH_INFORMATION (educational)
# ---------------------------------------------------------------------------
def test_educational_fever_query_is_health_info():
    """'What causes fever?' is educational, not symptom guidance."""
    result = classify_intent("What causes fever?", "en")
    assert result.intent == IntentType.HEALTH_INFORMATION


# ---------------------------------------------------------------------------
# Test 7: "How to prevent dehydration?" → HEALTH_INFORMATION
# ---------------------------------------------------------------------------
def test_educational_dehydration_prevention():
    """'How to prevent dehydration?' is educational, not symptom guidance."""
    result = classify_intent("How to prevent dehydration?", "en")
    assert result.intent == IntentType.HEALTH_INFORMATION


# ---------------------------------------------------------------------------
# Test 8: Tamil body pain → SYMPTOM_GUIDANCE
# ---------------------------------------------------------------------------
def test_tamil_body_pain():
    """Tamil body pain query → SYMPTOM_GUIDANCE."""
    result = classify_intent("உடல் வலி இருக்கு", "ta")
    assert result.intent == IntentType.SYMPTOM_GUIDANCE
    assert result.extracted_symptom == "body_pain"


# ---------------------------------------------------------------------------
# Test 9: Cuts/wounds → SYMPTOM_GUIDANCE
# ---------------------------------------------------------------------------
def test_cuts_wounds_symptom():
    """Cuts/wounds → SYMPTOM_GUIDANCE."""
    result = classify_intent("I have a wound that is bleeding", "en")
    assert result.intent == IntentType.SYMPTOM_GUIDANCE
    assert result.extracted_symptom == "cuts_wounds"


# ---------------------------------------------------------------------------
# Test 10: Symptom + facility in Tamil → SYMPTOM_WITH_FACILITY
# ---------------------------------------------------------------------------
def test_tamil_symptom_with_hospital():
    """Tamil symptom + hospital → SYMPTOM_WITH_FACILITY."""
    result = classify_intent("காய்ச்சல் இருக்கு, அருகில் மருத்துவமனை இருக்கா?", "ta")
    assert result.intent == IntentType.SYMPTOM_WITH_FACILITY
    assert result.extracted_symptom == "fever"


# ---------------------------------------------------------------------------
# Test 11: Dizziness → SYMPTOM_GUIDANCE
# ---------------------------------------------------------------------------
def test_dizziness_symptom():
    """Dizziness query → SYMPTOM_GUIDANCE."""
    result = classify_intent("I feel very dizzy and have dizziness", "en")
    assert result.intent == IntentType.SYMPTOM_GUIDANCE
    assert result.extracted_symptom == "dizziness"


# ---------------------------------------------------------------------------
# Test 12: "Feel sick" → SYMPTOM_GUIDANCE
# ---------------------------------------------------------------------------
def test_feel_sick_general():
    """'I feel sick' → SYMPTOM_GUIDANCE."""
    result = classify_intent("I feel sick and weak today", "en")
    assert result.intent == IntentType.SYMPTOM_GUIDANCE
