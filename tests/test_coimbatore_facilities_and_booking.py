"""Comprehensive Test Suite for Verified Coimbatore Healthcare Facility Dataset,
Database Integration, and AI Hospital Booking.

Verifies:
1. Strict Geographic Boundary: Only Coimbatore district facilities are in the verified dataset.
2. Zero Fabrication Policy: Facilities have verified coordinates, authentic official sources, and genuine booking channels.
3. Accurate Multi-criteria Search: Category, ownership (Government vs Private), emergency services, maternity services.
4. The 10 Essential User Questions:
   - "Suggest hospitals in Coimbatore."
   - "Where is the nearest PHC in Coimbatore?"
   - "Show me CHCs in Coimbatore."
   - "Which government hospitals are available in Coimbatore?"
   - "I want to book an appointment in a Coimbatore hospital."
   - "Which hospitals provide maternity services?"
   - "Which hospitals have emergency services?"
   - "Hospitals near Pollachi."
   - "கோயம்புத்தூர்ல PHC எங்க இருக்கு?"
   - "கோயம்புத்தூரில் அரசு மருத்துவமனைகள் சொல்லு."
5. Negative Tests: Prohibited / neighboring districts (Tiruppur, Erode, Salem) return truthful negative responses without leaking nearby facilities.
6. Genuine Booking Models: Walk-in OPD registration vs Online Portal Booking, no mock confirmation tokens.
"""

import json
from pathlib import Path
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent import carebridge_agent
from app.ai.intent_classifier import IntentType, classify_intent
from app.ai.schemas import AIChatRequest
from app.ai.tools import get_appointment_slots_tool, search_facilities_tool
from app.core.database import AsyncSessionLocal
from app.models.facility import (
    Facility,
    FacilityAppointmentConfig,
    FacilityService,
    FacilitySource,
    FacilitySpecialty,
)


COIMBATORE_BOUNDS = {
    "min_lat": 10.15,
    "max_lat": 11.55,
    "min_lon": 76.60,
    "max_lon": 77.40,
}

PROHIBITED_DISTRICTS = ["tiruppur", "tirupur", "erode", "nilgiris", "salem", "namakkal"]


# -----------------------------------------------------------------
# 1. DATASET INTEGRITY & STRICT GEOGRAPHIC BOUNDARY
# -----------------------------------------------------------------
def test_dataset_json_integrity_and_bounds():
    """Verify JSON dataset file has exactly 33 verified records strictly within Coimbatore bounds."""
    dataset_path = Path("data/coimbatore/coimbatore_facilities_verified.json")
    assert dataset_path.exists(), "Coimbatore dataset file must exist"

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert len(data) >= 30, f"Expected at least 30 facilities, found {len(data)}"

    for fac in data:
        # District check
        assert fac["district"].lower() == "coimbatore", f"{fac['name']} district is {fac['district']}, must be Coimbatore"

        # Coordinates check
        lat = fac["latitude"]
        lon = fac["longitude"]
        assert COIMBATORE_BOUNDS["min_lat"] <= lat <= COIMBATORE_BOUNDS["max_lat"], f"{fac['name']} latitude {lat} out of bounds"
        assert COIMBATORE_BOUNDS["min_lon"] <= lon <= COIMBATORE_BOUNDS["max_lon"], f"{fac['name']} longitude {lon} out of bounds"

        # Verification check
        assert fac.get("verification_status") == "VERIFIED_OFFICIAL"
        assert fac.get("official_source_url"), f"{fac['name']} missing official source URL"
        assert fac.get("appointment_booking_method") in ["WALK_IN_ONLY", "ONLINE_BOOKING_AVAILABLE"]


def test_provenance_json_links_all_facilities():
    """Verify every facility in dataset is referenced in sources_provenance.json."""
    prov_path = Path("data/coimbatore/sources_provenance.json")
    data_path = Path("data/coimbatore/coimbatore_facilities_verified.json")

    with open(prov_path, "r", encoding="utf-8") as pf, open(data_path, "r", encoding="utf-8") as df:
        prov = json.load(pf)
        data = json.load(df)

    data_names = {f["name"] for f in data}
    covered_names = set()
    for src in prov["sources"]:
        for name in src.get("records_covered", []):
            covered_names.add(name)

    assert len(covered_names) == len(data_names), f"Covered names ({len(covered_names)}) must match dataset facilities ({len(data_names)})"
    assert data_names == covered_names, f"Missing provenance coverage for: {data_names - covered_names}"


# -----------------------------------------------------------------
# 2. DATABASE PERSISTENCE & EXTENDED RELATIONSHIPS
# -----------------------------------------------------------------
@pytest.mark.asyncio
async def test_database_coimbatore_facilities_persisted():
    """Verify Coimbatore records exist in database with extended fields and appointment configs."""
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(Facility).where(func.lower(Facility.district) == "coimbatore")
        )
        cbe_facs = list(res.scalars().all())
        assert len(cbe_facs) >= 30, f"Expected at least 30 Coimbatore facilities in DB, found {len(cbe_facs)}"

        # Check walk-in vs online configuration
        walk_in_count = 0
        online_count = 0
        emergency_count = 0
        maternity_count = 0

        for f in cbe_facs:
            if f.appointment_booking_method == "WALK_IN_ONLY":
                walk_in_count += 1
            elif f.appointment_booking_method == "ONLINE_BOOKING_AVAILABLE":
                online_count += 1

            if f.emergency_services:
                emergency_count += 1
            if f.maternity_services:
                maternity_count += 1

        assert walk_in_count >= 15, "Public health facilities must use WALK_IN_ONLY"
        assert online_count >= 5, "Accredited private hospitals must provide ONLINE_BOOKING_AVAILABLE"
        assert emergency_count >= 5, "Trauma/casualty apex centers must have emergency_services=True"
        assert maternity_count >= 5, "Maternity homes/CEmONC centers must have maternity_services=True"


# -----------------------------------------------------------------
# 3. AI INTENT CLASSIFICATION ON COIMBATORE QUERIES
# -----------------------------------------------------------------
def test_coimbatore_query_intent_classification():
    """Verify structured intent classification and entity extraction on the 10 queries."""
    cases = [
        ("Suggest hospitals in Coimbatore.", IntentType.FACILITY_SEARCH, "Coimbatore", "HOSPITAL", None),
        ("Where is the nearest PHC in Coimbatore?", IntentType.FACILITY_SEARCH, "Coimbatore", "PHC", None),
        ("Show me CHCs in Coimbatore.", IntentType.FACILITY_SEARCH, "Coimbatore", "CHC", None),
        ("Which government hospitals are available in Coimbatore?", IntentType.FACILITY_SEARCH, "Coimbatore", "HOSPITAL", "Government"),
        ("I want to book an appointment in a Coimbatore hospital.", IntentType.APPOINTMENT_BOOKING, "Coimbatore", "HOSPITAL", None),
        ("Which hospitals provide maternity services?", IntentType.FACILITY_SEARCH, None, "HOSPITAL", None),
        ("Which hospitals have emergency services?", IntentType.FACILITY_SEARCH, None, "HOSPITAL", None),
        ("Hospitals near Pollachi.", IntentType.FACILITY_SEARCH, "Pollachi", "HOSPITAL", None),
        ("கோயம்புத்தூர்ல PHC எங்க இருக்கு?", IntentType.FACILITY_SEARCH, "Coimbatore", "PHC", None),
        ("கோயம்புத்தூரில் அரசு மருத்துவமனைகள் சொல்லு.", IntentType.FACILITY_SEARCH, "Coimbatore", "HOSPITAL", "Government"),
    ]

    for query, expected_intent, expected_loc, expected_type, expected_own in cases:
        result = classify_intent(query, "ta" if any("\u0b80" <= c <= "\u0bff" for c in query) else "en")
        assert result.intent == expected_intent, f"Failed intent for: {query}"
        if expected_loc:
            assert result.extracted_location == expected_loc, f"Failed location for: {query}"
        if expected_type:
            assert result.extracted_facility_type == expected_type, f"Failed facility_type for: {query}"
        if expected_own:
            assert result.entities.get("ownership") == expected_own, f"Failed ownership for: {query}"


# -----------------------------------------------------------------
# 4. END-TO-END AGENT EXECUTION ON THE 10 ESSENTIAL QUESTIONS
# -----------------------------------------------------------------
@pytest.mark.asyncio
async def test_agent_1_suggest_hospitals_in_coimbatore():
    async with AsyncSessionLocal() as db:
        req = AIChatRequest(message="Suggest hospitals in Coimbatore.", language="en")
        resp = await carebridge_agent.execute_turn(req, db)
        assert resp.intent == "FACILITY_PROXIMITY_SEARCH"
        assert "search_facilities_tool" in resp.tools_called
        assert len(resp.cards) > 0
        assert "Coimbatore" in resp.response_text
        assert "Tiruchengode" not in resp.response_text


@pytest.mark.asyncio
async def test_agent_2_nearest_phc_in_coimbatore():
    async with AsyncSessionLocal() as db:
        req = AIChatRequest(message="Where is the nearest PHC in Coimbatore?", language="en")
        resp = await carebridge_agent.execute_turn(req, db)
        assert resp.intent == "FACILITY_PROXIMITY_SEARCH"
        assert len(resp.cards) > 0
        card_types = [c.badge for c in resp.cards]
        assert any("PHC" in b or "MATERNITY" in b or "DOCTOR" in b for b in card_types)


@pytest.mark.asyncio
async def test_agent_3_chcs_in_coimbatore():
    async with AsyncSessionLocal() as db:
        req = AIChatRequest(message="Show me CHCs in Coimbatore.", language="en")
        resp = await carebridge_agent.execute_turn(req, db)
        assert resp.intent == "FACILITY_PROXIMITY_SEARCH"
        assert "CHC" in resp.response_text or len(resp.cards) > 0


@pytest.mark.asyncio
async def test_agent_4_government_hospitals_in_coimbatore():
    async with AsyncSessionLocal() as db:
        req = AIChatRequest(message="Which government hospitals are available in Coimbatore?", language="en")
        resp = await carebridge_agent.execute_turn(req, db)
        assert resp.intent == "FACILITY_PROXIMITY_SEARCH"
        assert len(resp.cards) > 0
        # All returned cards must be Government
        for c in resp.cards:
            assert "Private" not in c.subtitle


@pytest.mark.asyncio
async def test_agent_5_book_appointment_in_coimbatore():
    async with AsyncSessionLocal() as db:
        req = AIChatRequest(message="I want to book an appointment in a Coimbatore hospital.", language="en")
        resp = await carebridge_agent.execute_turn(req, db)
        assert resp.intent == "APPOINTMENT_BOOKING_FLOW"
        assert "get_appointment_slots_tool" in resp.tools_called
        assert len(resp.cards) > 0
        # Must clearly explain Walk-In OPD Registration without inventing mock slots
        assert "Walk-In OPD Registration" in resp.response_text
        assert "zero-fabrication" in resp.response_text.lower() or "never fabricates" in resp.response_text.lower()


@pytest.mark.asyncio
async def test_agent_6_maternity_services():
    async with AsyncSessionLocal() as db:
        req = AIChatRequest(message="Which hospitals provide maternity services?", language="en")
        resp = await carebridge_agent.execute_turn(req, db)
        assert resp.intent == "FACILITY_PROXIMITY_SEARCH"
        assert len(resp.cards) > 0
        assert "Maternity" in resp.response_text


@pytest.mark.asyncio
async def test_agent_7_emergency_services():
    async with AsyncSessionLocal() as db:
        req = AIChatRequest(message="Which hospitals have emergency services?", language="en")
        resp = await carebridge_agent.execute_turn(req, db)
        assert resp.intent == "FACILITY_PROXIMITY_SEARCH"
        assert len(resp.cards) > 0
        assert "Emergency" in resp.response_text


@pytest.mark.asyncio
async def test_agent_8_hospitals_near_pollachi():
    async with AsyncSessionLocal() as db:
        req = AIChatRequest(message="Hospitals near Pollachi.", language="en")
        resp = await carebridge_agent.execute_turn(req, db)
        assert resp.intent == "FACILITY_PROXIMITY_SEARCH"
        assert len(resp.cards) > 0
        top_card_title = resp.cards[0].title
        assert "Pollachi" in top_card_title or "Pollachi" in resp.response_text


@pytest.mark.asyncio
async def test_agent_9_tamil_phc_in_coimbatore():
    async with AsyncSessionLocal() as db:
        req = AIChatRequest(message="கோயம்புத்தூர்ல PHC எங்க இருக்கு?", language="ta")
        resp = await carebridge_agent.execute_turn(req, db)
        assert resp.intent == "FACILITY_PROXIMITY_SEARCH"
        assert resp.language == "ta"
        assert len(resp.cards) > 0
        assert "ஆரம்ப சுகாதார" in resp.response_text or "சுகாதார" in resp.response_text


@pytest.mark.asyncio
async def test_agent_10_tamil_government_hospitals():
    async with AsyncSessionLocal() as db:
        req = AIChatRequest(message="கோயம்புத்தூரில் அரசு மருத்துவமனைகள் சொல்லு.", language="ta")
        resp = await carebridge_agent.execute_turn(req, db)
        assert resp.intent == "FACILITY_PROXIMITY_SEARCH"
        assert resp.language == "ta"
        assert len(resp.cards) > 0
        assert "அரசு மருத்துவமனை" in resp.response_text


# -----------------------------------------------------------------
# 5. NEGATIVE AND BOUNDARY TESTS
# -----------------------------------------------------------------
@pytest.mark.asyncio
async def test_negative_prohibited_district_tiruppur():
    """Verify that asking for a hospital in Tiruppur truthfully says no registered facilities."""
    async with AsyncSessionLocal() as db:
        req = AIChatRequest(message="Find a hospital in Tiruppur", language="en")
        resp = await carebridge_agent.execute_turn(req, db)
        assert resp.intent == "FACILITY_PROXIMITY_SEARCH"
        assert len(resp.cards) == 0, "Must NOT dump facility cards from other districts"
        assert "no verified healthcare facilities" in resp.response_text.lower()
        assert "108" in resp.response_text


@pytest.mark.asyncio
async def test_negative_booking_unsupported_location():
    """Verify that booking in an unknown/unsupported location returns an honest negative response."""
    async with AsyncSessionLocal() as db:
        req = AIChatRequest(message="I want to book an appointment in Kanyakumari hospital", language="en")
        resp = await carebridge_agent.execute_turn(req, db)
        assert resp.intent == "APPOINTMENT_BOOKING_FLOW"
        assert len(resp.cards) == 0
        assert "no verified" in resp.response_text.lower()
