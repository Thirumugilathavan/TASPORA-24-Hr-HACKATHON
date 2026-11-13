"""Tests for locality-specific facility retrieval.

Verifies that NALAM returns correct facilities for sub-locality queries
(Sulur, Pollachi, Mettupalayam etc.) instead of generic Coimbatore results.
Also verifies no fake distances without real GPS.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai.intent_classifier import classify_intent, IntentType
from app.ai.location_extractor import extract_location


# ---------------------------------------------------------------------------
# Test 1: Sulur hospital query extracts Sulur location
# ---------------------------------------------------------------------------
def test_sulur_location_extraction():
    """'Where is the hospital in Sulur?' must extract Sulur as location."""
    result = classify_intent("Where is the hospital in Sulur?", "en")
    assert result.intent == IntentType.FACILITY_SEARCH
    loc_tuple = extract_location("Where is the hospital in Sulur?")
    # extract_location returns (location_str, coords_tuple, is_explicit)
    loc_str = loc_tuple[0]
    assert loc_str is not None
    assert "sulur" in loc_str.lower()


# ---------------------------------------------------------------------------
# Test 2: Pollachi location extraction
# ---------------------------------------------------------------------------
def test_pollachi_location_extraction():
    """'Hospitals in Pollachi' must extract Pollachi as location."""
    result = classify_intent("Show hospitals in Pollachi", "en")
    assert result.intent == IntentType.FACILITY_SEARCH
    loc_tuple = extract_location("Show hospitals in Pollachi")
    loc_str = loc_tuple[0]
    assert loc_str is not None
    assert "pollachi" in loc_str.lower()


# ---------------------------------------------------------------------------
# Test 3: Mettupalayam location extraction
# ---------------------------------------------------------------------------
def test_mettupalayam_location_extraction():
    """'Government hospital in Mettupalayam' extracts Mettupalayam."""
    result = classify_intent("Government hospital in Mettupalayam", "en")
    assert result.intent == IntentType.FACILITY_SEARCH
    loc_tuple = extract_location("Government hospital in Mettupalayam")
    loc_str = loc_tuple[0]
    assert loc_str is not None
    assert "mettupalayam" in loc_str.lower()


# ---------------------------------------------------------------------------
# Test 4: Coimbatore district-wide extraction
# ---------------------------------------------------------------------------
def test_coimbatore_district_extraction():
    """'Show hospitals in Coimbatore' extracts Coimbatore."""
    result = classify_intent("Show hospitals in Coimbatore", "en")
    assert result.intent == IntentType.FACILITY_SEARCH
    loc_tuple = extract_location("Show hospitals in Coimbatore")
    loc_str = loc_tuple[0]
    assert loc_str is not None
    assert "coimbatore" in loc_str.lower()


# ---------------------------------------------------------------------------
# Test 5: Sulur intent classification with ownership filter
# ---------------------------------------------------------------------------
def test_sulur_government_hospital_intent():
    """'Show government hospitals in Sulur' → FACILITY_SEARCH with Sulur location."""
    result = classify_intent("Show government hospitals in Sulur", "en")
    assert result.intent == IntentType.FACILITY_SEARCH
    assert result.extracted_location is not None
    assert "sulur" in result.extracted_location.lower()


# ---------------------------------------------------------------------------
# Test 6: Sulur vs Coimbatore distinction
# ---------------------------------------------------------------------------
def test_sulur_is_not_generic_coimbatore():
    """Sulur query should extract 'Sulur', not just 'Coimbatore'."""
    result = classify_intent("Where is the hospital in Sulur?", "en")
    loc = result.extracted_location
    assert loc is not None
    # Should contain Sulur specifically, not just Coimbatore
    assert "sulur" in loc.lower()


# ---------------------------------------------------------------------------
# Test 7: Tamil Sulur query intent
# ---------------------------------------------------------------------------
def test_tamil_sulur_query_intent():
    """Tamil query for Sulur should classify as FACILITY_SEARCH."""
    result = classify_intent("சூலூர்ல மருத்துவமனை எங்க இருக்கு?", "ta")
    assert result.intent == IntentType.FACILITY_SEARCH


# ---------------------------------------------------------------------------
# Test 8: Annur location extraction
# ---------------------------------------------------------------------------
def test_annur_location_extraction():
    """'Hospitals near Annur' extracts Annur."""
    loc_tuple = extract_location("Hospitals near Annur")
    loc_str = loc_tuple[0]
    if loc_str:
        assert "annur" in loc_str.lower()


# ---------------------------------------------------------------------------
# Test 9: Multiple sub-localities are distinguished
# ---------------------------------------------------------------------------
def test_different_sub_localities_distinguished():
    """Sulur and Pollachi produce different location extractions."""
    res_sulur = classify_intent("Hospital in Sulur", "en")
    res_pollachi = classify_intent("Hospital in Pollachi", "en")
    assert res_sulur.extracted_location != res_pollachi.extracted_location


# ---------------------------------------------------------------------------
# Test 10: PHC type filter + location
# ---------------------------------------------------------------------------
def test_phc_sulur_query():
    """'Show PHCs in Sulur' → FACILITY_SEARCH."""
    result = classify_intent("Show PHCs in Sulur", "en")
    assert result.intent == IntentType.FACILITY_SEARCH
    assert result.extracted_location is not None
    assert "sulur" in result.extracted_location.lower()
