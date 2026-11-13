"""
Automated Test Suite for NALAM Scheme Finder — Government Schemes & Financial Benefits.
Covers:
- Questionnaire config & privacy notice
- Consented profile prefill, persistence, isolation, and consent withdrawal
- Deterministic eligibility rules (income, age, gender, farming, education, disability, widow)
- Scheme recommendations scoring and ranking
- Verified official portals & document requirements
- Saved schemes bookmarks & side-by-side comparison
- Document checklist aggregator
- AI Assistant query_government_schemes_tool integration
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.patient import Patient
from app.models.village import Village
from app.models.scheme import GovernmentScheme, UserSchemeProfile, SavedUserScheme
from app.services.scheme_recommendation_service import SchemeRecommendationEngine
from app.ai.agent import NalamAIAgent
from app.ai.schemas import AIChatRequest


@pytest.mark.asyncio
async def test_questionnaire_configuration_endpoint(client: AsyncClient):
    """Verifies questionnaire steps, disclosures, and metadata are returned."""
    resp = await client.get("/api/v1/schemes/questionnaire/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_steps"] == 8
    assert "privacy_notice_en" in data
    assert "privacy_notice_ta" in data
    assert len(data["steps"]) == 8
    step_ids = [s["id"] for s in data["steps"]]
    assert "basic" in step_ids
    assert "household" in step_ids
    assert "financial" in step_ids
    assert "social" in step_ids
    assert "education_employment" in step_ids
    assert "agriculture_business" in step_ids
    assert "healthcare_needs" in step_ids
    assert "financial_needs" in step_ids


@pytest.mark.asyncio
async def test_scheme_registry_listing_and_detail(client: AsyncClient, seed_data: dict):
    """Verifies verified government schemes are listed and details retrievable."""
    resp = await client.get("/api/v1/schemes/")
    assert resp.status_code == 200
    schemes = resp.json()
    assert len(schemes) >= 10

    # Find CMCHIS scheme
    cmchis = next((s for s in schemes if "cmchis" in s["slug"]), None)
    assert cmchis is not None
    assert cmchis["level"] == "STATE"
    assert cmchis["category"] == "HEALTHCARE"
    assert "cmchistn.com" in cmchis["official_portal_url"]

    # Retrieve full detail
    detail_resp = await client.get(f"/api/v1/schemes/{cmchis['id']}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert len(detail["required_documents"]) >= 3
    assert any(d["name_en"] == "Smart Ration Card / Family Card" for d in detail["required_documents"])


@pytest.mark.asyncio
async def test_profile_prefill_from_existing_patient_record(
    client: AsyncClient,
    seed_data: dict,
):
    """Verifies that an authenticated patient has their basic location and age prefilled."""
    patient_headers = seed_data["headers"]["patient"]
    resp = await client.get("/api/v1/schemes/profile", headers=patient_headers)
    assert resp.status_code == 200
    profile = resp.json()
    assert profile["prefilled_from_profile"] is True
    # Verify prefilled basic info from seeded patient
    assert profile["profile_data"]["basic"]["state"] == "Tamil Nadu"
    assert profile["profile_data"]["basic"]["age"] is not None


@pytest.mark.asyncio
async def test_save_and_delete_user_scheme_profile(
    client: AsyncClient,
    seed_data: dict,
):
    """Verifies user can save questionnaire answers and delete them to withdraw consent."""
    patient_headers = seed_data["headers"]["patient"]

    payload = {
        "consent_given": True,
        "step_progress": 8,
        "profile_data": {
            "basic": {"age": 28, "state": "Tamil Nadu", "district": "Vellore", "residence_type": "RURAL"},
            "household": {"family_size": 3, "is_female_headed": True, "marital_status": "MARRIED"},
            "financial": {"annual_income": 80000, "income_range": "BELOW_1_LAKH", "has_ration_card": True, "ration_card_type": "PHH"},
            "social": {"is_woman_seeking_aid": True, "community_category": "OBC"},
            "education_employment": {"current_education_status": "NOT_STUDYING"},
            "agriculture_business": {"owns_agricultural_land": False},
            "healthcare_needs": {"needs_health_insurance": True},
            "financial_needs": ["WOMEN_CHILD", "HEALTHCARE"],
        },
    }

    save_resp = await client.post("/api/v1/schemes/profile", json=payload, headers=patient_headers)
    assert save_resp.status_code == 200
    saved = save_resp.json()
    assert saved["consent_given"] is True
    assert saved["step_progress"] == 8
    assert saved["profile_data"]["basic"]["district"] == "Vellore"

    # Delete / Withdraw consent
    del_resp = await client.delete("/api/v1/schemes/profile", headers=patient_headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"


@pytest.mark.asyncio
async def test_cmchis_recommendation_for_low_income_tamil_nadu_family(
    client: AsyncClient,
    seed_data: dict,
):
    """Verifies that a low-income family in Tamil Nadu with a ration card is LIKELY_ELIGIBLE for CMCHIS."""
    patient_headers = seed_data["headers"]["patient"]

    profile_payload = {
        "consent_given": True,
        "step_progress": 8,
        "profile_data": {
            "basic": {"age": 42, "state": "Tamil Nadu", "district": "Salem", "residence_type": "RURAL"},
            "household": {"family_size": 4, "is_female_headed": False, "marital_status": "MARRIED"},
            "financial": {"annual_income": 95000, "income_range": "BELOW_1_LAKH", "has_ration_card": True, "ration_card_type": "PHH"},
            "social": {"community_category": "MBC"},
            "healthcare_needs": {"needs_health_insurance": True},
            "financial_needs": ["HEALTHCARE"],
        },
    }
    await client.post("/api/v1/schemes/profile", json=profile_payload, headers=patient_headers)

    rec_resp = await client.get("/api/v1/schemes/recommendations?language=en", headers=patient_headers)
    assert rec_resp.status_code == 200
    data = rec_resp.json()

    cmchis_eval = next((r for r in data["recommendations"] if "cmchis" in r["scheme"]["slug"]), None)
    assert cmchis_eval is not None
    assert cmchis_eval["eligibility_status"] == "LIKELY_ELIGIBLE"
    assert cmchis_eval["match_score"] >= 85.0
    assert any("Income satisfies threshold" in reason for reason in cmchis_eval["matched_reasons"])


@pytest.mark.asyncio
async def test_kmut_recommendation_for_female_head_of_household(
    client: AsyncClient,
    seed_data: dict,
):
    """Verifies that a female head of family aged 21+ with low income matches Kalaignar Magalir Urimai Thittam."""
    patient_headers = seed_data["headers"]["patient"]

    profile_payload = {
        "consent_given": True,
        "step_progress": 8,
        "profile_data": {
            "basic": {"age": 34, "state": "Tamil Nadu", "district": "Namakkal", "residence_type": "RURAL"},
            "household": {"family_size": 4, "is_female_headed": True, "marital_status": "MARRIED"},
            "financial": {"annual_income": 120000, "income_range": "1_TO_2.5_LAKH", "has_ration_card": True},
            "social": {"community_category": "BC", "is_woman_seeking_aid": True},
            "agriculture_business": {"owns_agricultural_land": False},
            "financial_needs": ["WOMEN_CHILD"],
        },
    }
    await client.post("/api/v1/schemes/profile", json=profile_payload, headers=patient_headers)

    rec_resp = await client.get("/api/v1/schemes/recommendations?language=ta", headers=patient_headers)
    assert rec_resp.status_code == 200
    data = rec_resp.json()

    kmut_eval = next((r for r in data["recommendations"] if "kmut" in r["scheme"]["slug"]), None)
    assert kmut_eval is not None
    assert kmut_eval["eligibility_status"] in ["LIKELY_ELIGIBLE", "POSSIBLY_ELIGIBLE"]
    assert kmut_eval["match_score"] >= 75.0


@pytest.mark.asyncio
async def test_pm_kisan_recommendation_for_landholding_farmer(
    client: AsyncClient,
    seed_data: dict,
):
    """Verifies that an agricultural landholder matches PM-KISAN."""
    patient_headers = seed_data["headers"]["patient"]

    profile_payload = {
        "consent_given": True,
        "step_progress": 8,
        "profile_data": {
            "basic": {"age": 45, "state": "Tamil Nadu", "district": "Erode", "residence_type": "RURAL"},
            "financial": {"annual_income": 110000, "income_source": "AGRICULTURE"},
            "social": {"is_farmer": True},
            "agriculture_business": {"owns_agricultural_land": True, "land_acres": 2.5, "farmer_category": "SMALL_MARGINAL"},
            "financial_needs": ["AGRICULTURE"],
        },
    }
    await client.post("/api/v1/schemes/profile", json=profile_payload, headers=patient_headers)

    rec_resp = await client.get("/api/v1/schemes/recommendations?language=en", headers=patient_headers)
    assert rec_resp.status_code == 200
    data = rec_resp.json()

    kisan_eval = next((r for r in data["recommendations"] if "kisan" in r["scheme"]["slug"]), None)
    assert kisan_eval is not None
    assert kisan_eval["eligibility_status"] in ["LIKELY_ELIGIBLE", "POSSIBLY_ELIGIBLE"]
    assert any("landholder criteria matches" in r for r in kisan_eval["matched_reasons"])


@pytest.mark.asyncio
async def test_deterministic_engine_hard_fails_ineligible_criteria(
    client: AsyncClient,
    seed_data: dict,
    db_session: AsyncSession,
):
    """Verifies that a male non-widow or high income earner is marked NOT_ELIGIBLE."""
    await SchemeRecommendationEngine.seed_verified_schemes_if_empty(db_session)

    stmt = select(GovernmentScheme).where(GovernmentScheme.slug == "destitute-widow-pension-tn")
    widow_scheme = (await db_session.execute(stmt)).scalar_one()

    # User is male, not widow
    ineligible_data = {
        "basic": {"age": 30, "gender": "MALE", "state": "Tamil Nadu"},
        "household": {"is_female_headed": False},
        "social": {"is_widow": False},
    }
    eval_res = SchemeRecommendationEngine.evaluate_scheme_eligibility(ineligible_data, widow_scheme)
    assert eval_res.eligibility_status == "NOT_ELIGIBLE"
    assert eval_res.match_score <= 15.0


@pytest.mark.asyncio
async def test_saved_schemes_bookmarking_crud(
    client: AsyncClient,
    seed_data: dict,
):
    """Verifies saving, retrieving, and removing bookmarked schemes."""
    patient_headers = seed_data["headers"]["patient"]

    # 1. Get first scheme
    schemes_resp = await client.get("/api/v1/schemes/")
    first_scheme_id = schemes_resp.json()[0]["id"]

    # 2. Save it
    save_resp = await client.post(
        f"/api/v1/schemes/{first_scheme_id}/save",
        json={"notes": "Priority health scheme for my family"},
        headers=patient_headers,
    )
    assert save_resp.status_code in [201, 200]

    # 3. List saved
    list_resp = await client.get("/api/v1/schemes/user/saved", headers=patient_headers)
    assert list_resp.status_code == 200
    saved_list = list_resp.json()
    assert any(s["scheme_id"] == first_scheme_id for s in saved_list)

    # 4. Remove it
    del_resp = await client.delete(f"/api/v1/schemes/{first_scheme_id}/save", headers=patient_headers)
    assert del_resp.status_code == 200


@pytest.mark.asyncio
async def test_scheme_comparison_endpoint(
    client: AsyncClient,
    seed_data: dict,
):
    """Verifies side-by-side scheme comparison data structure."""
    schemes_resp = await client.get("/api/v1/schemes/")
    all_schemes = schemes_resp.json()
    assert len(all_schemes) >= 2

    compare_ids = [all_schemes[0]["id"], all_schemes[1]["id"]]
    comp_resp = await client.post("/api/v1/schemes/compare", json={"scheme_ids": compare_ids})
    assert comp_resp.status_code == 200
    comp_data = comp_resp.json()
    assert len(comp_data["schemes"]) == 2
    assert len(comp_data["comparison_fields"]) >= 5


@pytest.mark.asyncio
async def test_document_checklist_aggregator(
    client: AsyncClient,
    seed_data: dict,
):
    """Verifies deduplicated document checklist separates mandatory and optional documents."""
    patient_headers = seed_data["headers"]["patient"]
    schemes_resp = await client.get("/api/v1/schemes/")
    scheme_ids = [s["id"] for s in schemes_resp.json()[:3]]

    chk_resp = await client.post(
        "/api/v1/schemes/documents/checklist",
        json={"scheme_ids": scheme_ids},
        headers=patient_headers,
    )
    assert chk_resp.status_code == 200
    chk_data = chk_resp.json()
    assert chk_data["total_documents"] > 0
    assert len(chk_data["mandatory_documents"]) > 0
    # Verify Aadhaar or Ration Card appears in mandatory list
    doc_names = [d["name_en"] for d in chk_data["mandatory_documents"]]
    assert any("Ration Card" in d or "Aadhaar" in d for d in doc_names)


@pytest.mark.asyncio
async def test_ai_agent_answers_government_scheme_queries_in_tamil_and_english(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Verifies NALAM AI Agent identifies scheme inquiries and responds with verified cards."""
    agent = NalamAIAgent()

    # English query about scholarships
    req_en = AIChatRequest(
        message="What government schemes and scholarships can I apply for as a student?",
        language="en",
    )
    resp_en = await agent.execute_turn(req_en, db_session)
    assert resp_en.intent == "GOVERNMENT_SCHEMES_DISCOVERY"
    assert "query_government_schemes_tool" in resp_en.tools_called
    assert len(resp_en.cards) > 0
    assert any(c.type == "SCHEME" for c in resp_en.cards)

    # Tamil query about medical schemes
    req_ta = AIChatRequest(
        message="எனக்கு என்ன அரசு மருத்துவ நலத்திட்டங்கள் மற்றும் காப்பீடுகள் கிடைக்கும்?",
        language="ta",
    )
    resp_ta = await agent.execute_turn(req_ta, db_session)
    assert resp_ta.intent == "GOVERNMENT_SCHEMES_DISCOVERY"
    assert resp_ta.language == "ta"
    assert len(resp_ta.cards) > 0
