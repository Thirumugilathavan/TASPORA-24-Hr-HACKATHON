"""
FastAPI router for NALAM Scheme Finder — Government Schemes & Financial Benefits.
Includes multi-step questionnaire config, consented profile persistence,
deterministic recommendations, saved schemes, comparisons, and document checklists.
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_, or_, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_optional_current_user
from app.models.user import User
from app.models.scheme import GovernmentScheme, UserSchemeProfile, SavedUserScheme, SchemeAuditLog
from app.schemas.scheme import (
    UserSchemeProfileIn,
    UserSchemeProfileOut,
    GovernmentSchemeBase,
    GovernmentSchemeDetailOut,
    SchemeRecommendationResponse,
    EligibilityEvaluationOut,
    SavedSchemeCreateIn,
    SavedSchemeOut,
    CompareSchemesIn,
    CompareSchemesOut,
    DocumentChecklistIn,
    DocumentChecklistOut,
    RequiredDocumentOut,
    QuestionnaireAnswersIn,
    SchemeMatchItemOut,
    SchemeMatchResponse,
    SchemeHealthResponse,
)
from app.services.scheme_recommendation_service import SchemeRecommendationEngine

router = APIRouter(prefix="/schemes", tags=["Government Schemes & Welfare"])


# -------------------------------------------------------------------------
# 1. Questionnaire Configuration & Privacy Disclosures
# -------------------------------------------------------------------------

@router.get("/questionnaire/config")
async def get_questionnaire_configuration():
    """
    Returns guided 8-step questionnaire metadata, questions, options,
    and privacy disclosure messages in English and Tamil.
    """
    return {
        "title_en": "Find Government Schemes & Subsidies for Me",
        "title_ta": "எனக்கான அரசு நலத்திட்டங்களை கண்டறிக",
        "privacy_notice_en": (
            "Privacy Notice: Your information is collected solely to assess your eligibility for government "
            "subsidies and financial welfare schemes. All questions are optional, and sensitive personal "
            "data is never shared with third parties or advertisers. You can edit or delete your profile at any time."
        ),
        "privacy_notice_ta": (
            "தனியுரிமை அறிவிப்பு: உங்கள் தகவல்கள் அரசு மானியங்கள் மற்றும் நலத்திட்டங்களுக்கான தகுதியை மதிப்பிடுவதற்கு "
            "மட்டுமே சேகரிக்கப்படுகின்றன. அனைத்து கேள்விகளும் விருப்பத்திற்குரியவை. உங்கள் தனிப்பட்ட தரவு மூன்றாம் "
            "தரப்பினருடன் பகிரப்படாது. எந்த நேரத்திலும் உங்கள் சுயவிவரத்தை நீக்கலாம்."
        ),
        "total_steps": 8,
        "steps": [
            {
                "step": 1,
                "id": "basic",
                "title_en": "Basic Personal Information",
                "title_ta": "அடிப்படை தனிநபர் தகவல்கள்",
                "description_en": "Age, residence, and location to determine territorial eligibility.",
                "description_ta": "வயது, வசிப்பிடம் மற்றும் இருப்பிட தகவல்கள்.",
            },
            {
                "step": 2,
                "id": "household",
                "title_en": "Household & Family Information",
                "title_ta": "குடும்ப விவரங்கள்",
                "description_en": "Family composition, dependents, and household structure.",
                "description_ta": "குடும்ப உறுப்பினர்கள், சார்ந்திருப்போர் மற்றும் தலைவர் விவரங்கள்.",
            },
            {
                "step": 3,
                "id": "financial",
                "title_en": "Financial & Ration Card Details",
                "title_ta": "பொருளாதார மற்றும் குடும்ப அட்டை விவரங்கள்",
                "description_en": "Income brackets and ration card status (no bank credentials requested).",
                "description_ta": "வருமான வரம்பு மற்றும் ரேஷன் அட்டை வகை (வங்கி ரகசிய எண்கள் கேட்கப்படாது).",
            },
            {
                "step": 4,
                "id": "social",
                "title_en": "Social & Category Eligibility",
                "title_ta": "சமூக மற்றும் சிறப்பு தகுதிகள்",
                "description_en": "Special beneficiary categories such as senior citizens, widows, and persons with disabilities.",
                "description_ta": "முதியோர், ஆதரவற்ற விதவை, மாற்றுத்திறனாளி உள்ளிட்ட சிறப்பு தகுதிகள்.",
            },
            {
                "step": 5,
                "id": "education_employment",
                "title_en": "Education & Employment",
                "title_ta": "கல்வி மற்றும் வேலைவாய்ப்பு",
                "description_en": "Qualifications, school/college status, and scholarship interests.",
                "description_ta": "கல்வித் தகுதி, பள்ளி/கல்லூரி படிப்பு மற்றும் உதவித்தொகை தேவைகள்.",
            },
            {
                "step": 6,
                "id": "agriculture_business",
                "title_en": "Agriculture & Business (Conditional)",
                "title_ta": "விவசாயம் மற்றும் தொழில் விவரங்கள்",
                "description_en": "Landholding for farmers and enterprise scale for business owners.",
                "description_ta": "விவசாய நில விவரங்கள் மற்றும் சிறு தொழில் விவரங்கள்.",
            },
            {
                "step": 7,
                "id": "healthcare_needs",
                "title_en": "Healthcare & Welfare Requirements",
                "title_ta": "சுகாதார மற்றும் மருத்துவத் தேவைகள்",
                "description_en": "Health insurance, maternal care, treatment financial aid, and medicine support.",
                "description_ta": "மருத்துவக் காப்பீடு, மகப்பேறு உதவி, சிகிச்சை நிதி மற்றும் மருந்து ஆதரவு.",
            },
            {
                "step": 8,
                "id": "financial_needs",
                "title_en": "Financial Assistance Needs",
                "title_ta": "தேவைப்படும் அரசு உதவிகள்",
                "description_en": "Select the types of welfare schemes you would like to discover.",
                "description_ta": "நீங்கள் அறிய விரும்பும் அரசு நலத்திட்ட வகைகளைத் தேர்ந்தெடுக்கவும்.",
            },
        ],
    }


# -------------------------------------------------------------------------
# 2. Consented User Scheme Profile Management
# -------------------------------------------------------------------------

@router.get("/profile", response_model=UserSchemeProfileOut)
async def get_user_scheme_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves the user's consented scheme profile. If not yet created,
    returns an intelligently prefilled template based on existing NALAM profile.
    """
    stmt = select(UserSchemeProfile).where(UserSchemeProfile.user_id == current_user.id)
    profile = (await db.execute(stmt)).scalar_one_or_none()

    if profile:
        return UserSchemeProfileOut(
            id=profile.id,
            user_id=profile.user_id,
            consent_given=profile.consent_given,
            consent_timestamp=profile.consent_timestamp,
            step_progress=profile.step_progress,
            profile_data=profile.profile_data,
            prefilled_from_profile=False,
        )

    # Prefill template
    prefilled_data, was_prefilled = await SchemeRecommendationEngine.get_or_prefill_user_profile(
        current_user.id, db
    )

    # Temporary response before user formally saves
    return UserSchemeProfileOut(
        id=current_user.id,  # temporary placeholder
        user_id=current_user.id,
        consent_given=False,
        consent_timestamp=None,
        step_progress=1,
        profile_data=prefilled_data,
        prefilled_from_profile=was_prefilled,
    )


@router.post("/profile", response_model=UserSchemeProfileOut)
async def save_user_scheme_profile(
    payload: UserSchemeProfileIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Saves or updates the user's questionnaire responses and consent.
    Ensures user data isolation.
    """
    stmt = select(UserSchemeProfile).where(UserSchemeProfile.user_id == current_user.id)
    profile = (await db.execute(stmt)).scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if profile:
        profile.consent_given = payload.consent_given
        profile.consent_timestamp = now if payload.consent_given else None
        profile.step_progress = payload.step_progress
        profile.profile_data = payload.profile_data
    else:
        profile = UserSchemeProfile(
            user_id=current_user.id,
            consent_given=payload.consent_given,
            consent_timestamp=now if payload.consent_given else None,
            step_progress=payload.step_progress,
            profile_data=payload.profile_data,
        )
        db.add(profile)

    await db.commit()
    await db.refresh(profile)

    return UserSchemeProfileOut(
        id=profile.id,
        user_id=profile.user_id,
        consent_given=profile.consent_given,
        consent_timestamp=profile.consent_timestamp,
        step_progress=profile.step_progress,
        profile_data=profile.profile_data,
        prefilled_from_profile=False,
    )


@router.delete("/profile", status_code=status.HTTP_200_OK)
async def delete_user_scheme_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Deletes the user's consented scheme profile and withdraws consent.
    """
    stmt = delete(UserSchemeProfile).where(UserSchemeProfile.user_id == current_user.id)
    await db.execute(stmt)
    await db.commit()
    return {"status": "success", "message": "Scheme profile deleted and consent withdrawn."}


# -------------------------------------------------------------------------
# 3. Personalized Scheme Recommendations & Questionnaire Matching
# -------------------------------------------------------------------------

@router.get("/health", response_model=SchemeHealthResponse)
async def get_schemes_service_health(db: AsyncSession = Depends(get_db)):
    """
    Reports the real-time operational health of the scheme recommendation service.
    """
    total_schemes = 0
    db_status = "connected"
    try:
        count_stmt = select(func.count(GovernmentScheme.id))
        total_schemes = (await db.execute(count_stmt)).scalar() or 0
        if total_schemes == 0:
            total_schemes = await SchemeRecommendationEngine.seed_verified_schemes_if_empty(db)
    except Exception as e:
        db_status = f"offline_fallback: {type(e).__name__}"
        total_schemes = len(SchemeRecommendationEngine.get_static_verified_schemes())

    return SchemeHealthResponse(
        status="ok",
        service="NALAM Government Schemes Recommendation Service",
        database=db_status,
        total_schemes=total_schemes,
        sources=[
            "National Government Services Portal (services.india.gov.in)",
            "myScheme Welfare Portal (myscheme.gov.in)",
            "Tamil Nadu e-Governance Agency (tnega.tn.gov.in)",
            "Chief Minister's Comprehensive Health Insurance Scheme (cmchistn.com)",
            "National Health Mission Tamil Nadu (nhm.tn.gov.in)",
            "PM-KISAN Samman Nidhi Portal (pmkisan.gov.in)",
        ],
        last_catalog_verification="November 2026",
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/match", response_model=SchemeMatchResponse)
async def match_schemes_from_questionnaire(
    payload: QuestionnaireAnswersIn,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluates questionnaire answers against verified government schemes.
    Deterministic, privacy-preserving, and accessible to both logged-in and guest users.
    """
    user_id = current_user.id if current_user else None
    return await SchemeRecommendationEngine.evaluate_questionnaire_matches(
        payload=payload,
        db=db,
        current_user_id=user_id,
    )


@router.get("/recommendations", response_model=SchemeRecommendationResponse)
async def get_scheme_recommendations(
    category: Optional[str] = Query(None, description="Filter by category"),
    level: Optional[str] = Query(None, description="Filter by CENTRAL or STATE"),
    language: str = Query("ta", pattern="^(ta|en)$", description="User preferred language"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluates profile against verified government schemes and returns recommendations.
    Supports authenticated users and guest users with safe defaults.
    """
    if current_user:
        return await SchemeRecommendationEngine.get_recommendations_for_user(
            user_id=current_user.id,
            db=db,
            language=language,
            category=category,
            level=level,
        )
    else:
        # Default anonymous recommendation based on general public priority
        default_answers = QuestionnaireAnswersIn(language=language)
        match_resp = await SchemeRecommendationEngine.evaluate_questionnaire_matches(
            default_answers, db=db, current_user_id=None
        )
        return SchemeRecommendationResponse(
            total_evaluated=match_resp.total_evaluated,
            likely_eligible_count=match_resp.likely_matches_count,
            possibly_eligible_count=match_resp.more_info_needed_count,
            more_info_count=match_resp.more_info_needed_count,
            recommendations=[
                EligibilityEvaluationOut(
                    scheme=item.scheme,
                    eligibility_status="LIKELY_ELIGIBLE" if item.match_status == "LIKELY_MATCH" else "POSSIBLY_ELIGIBLE",
                    match_score=item.match_score,
                    matched_reasons=item.reasons,
                    unverified_conditions=item.missing_information,
                    missing_fields=item.missing_information,
                    required_documents=item.required_documents,
                    is_saved=False,
                )
                for item in match_resp.all_results
            ],
            disclaimer=match_resp.disclaimer_en,
            disclaimer_ta=match_resp.disclaimer_ta,
        )


# -------------------------------------------------------------------------
# 4. Verified Government Schemes Catalog & Details
# -------------------------------------------------------------------------

@router.get("", response_model=List[GovernmentSchemeBase], include_in_schema=False)
@router.get("/", response_model=List[GovernmentSchemeBase])
async def list_government_schemes(
    category: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists all verified government schemes in the registry.
    Falls back gracefully to static verified catalog if database is temporarily unavailable.
    """
    schemes = []
    try:
        await SchemeRecommendationEngine.seed_verified_schemes_if_empty(db)
        stmt = select(GovernmentScheme).where(GovernmentScheme.is_active == True)

        if category and category != "ALL":
            stmt = stmt.where(GovernmentScheme.category == category)
        if level and level != "ALL":
            stmt = stmt.where(GovernmentScheme.level == level)
        if search:
            search_pattern = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(GovernmentScheme.name).like(search_pattern),
                    func.lower(GovernmentScheme.name_ta).like(search_pattern),
                    func.lower(GovernmentScheme.short_description).like(search_pattern),
                    func.lower(GovernmentScheme.short_description_ta).like(search_pattern),
                    func.lower(GovernmentScheme.department).like(search_pattern),
                )
            )

        stmt = stmt.order_by(GovernmentScheme.level.desc(), GovernmentScheme.name.asc()).offset(offset).limit(limit)
        schemes = list((await db.execute(stmt)).scalars().all())
    except Exception:
        schemes = []

    # Fallback to static catalog if DB is unreachable or returned empty
    if not schemes:
        all_static = SchemeRecommendationEngine.get_static_verified_schemes()
        filtered = all_static
        if category and category != "ALL":
            filtered = [s for s in filtered if s.category == category]
        if level and level != "ALL":
            filtered = [s for s in filtered if s.level == level]
        if search:
            q = search.strip().lower()
            filtered = [
                s for s in filtered
                if q in s.name.lower() or q in s.name_ta.lower() or q in s.short_description.lower() or q in s.department.lower()
            ]
        schemes = filtered[offset : offset + limit]

    return schemes


@router.get("/{scheme_id}", response_model=GovernmentSchemeDetailOut)
async def get_scheme_detail(
    scheme_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves full details, eligibility rules, required documents,
    and step-by-step application instructions for a single government scheme.
    Supports lookup by UUID or slug string, with database and static fallback.
    """
    scheme = None
    is_saved = False

    # 1. Try DB lookup
    try:
        try:
            uuid_obj = UUID(scheme_id)
            stmt = select(GovernmentScheme).where(GovernmentScheme.id == uuid_obj)
        except ValueError:
            stmt = select(GovernmentScheme).where(GovernmentScheme.slug == scheme_id)

        scheme = (await db.execute(stmt)).scalar_one_or_none()

        if scheme and current_user:
            s_stmt = select(SavedUserScheme).where(
                and_(
                    SavedUserScheme.user_id == current_user.id,
                    SavedUserScheme.scheme_id == scheme.id,
                )
            )
            is_saved = (await db.execute(s_stmt)).scalar_one_or_none() is not None
    except Exception:
        scheme = None

    # 2. Try static fallback if DB missed or failed
    if not scheme:
        all_static = SchemeRecommendationEngine.get_static_verified_schemes()
        for s in all_static:
            if str(s.id) == scheme_id or s.slug == scheme_id:
                scheme = s
                break

    if not scheme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Government scheme '{scheme_id}' not found in official registry.",
        )

    docs = [
        RequiredDocumentOut(
            name_en=d["name_en"],
            name_ta=d["name_ta"],
            is_mandatory=d.get("is_mandatory", True),
            description_en=d.get("description_en"),
            description_ta=d.get("description_ta"),
        )
        for d in (scheme.required_documents or [])
    ]

    return GovernmentSchemeDetailOut(
        id=scheme.id,
        slug=scheme.slug,
        name=scheme.name,
        name_ta=scheme.name_ta,
        short_description=scheme.short_description,
        short_description_ta=scheme.short_description_ta,
        detailed_description=scheme.detailed_description,
        detailed_description_ta=scheme.detailed_description_ta,
        department=scheme.department,
        department_ta=scheme.department_ta,
        level=scheme.level,
        state=scheme.state,
        districts=scheme.districts,
        category=scheme.category,
        target_beneficiaries=scheme.target_beneficiaries,
        target_beneficiaries_ta=scheme.target_beneficiaries_ta,
        benefit_type=scheme.benefit_type,
        benefit_amount_desc=scheme.benefit_amount_desc,
        benefit_amount_desc_ta=scheme.benefit_amount_desc_ta,
        benefit_frequency=scheme.benefit_frequency,
        eligibility_rules=scheme.eligibility_rules or {},
        required_documents=docs,
        application_mode=scheme.application_mode,
        application_process=scheme.application_process,
        application_process_ta=scheme.application_process_ta,
        official_portal_url=scheme.official_portal_url,
        official_source_url=scheme.official_source_url,
        is_active=scheme.is_active,
        application_status=scheme.application_status or "OPEN",
        last_verified_at=scheme.last_verified_at or datetime.now(timezone.utc),
        verification_status=scheme.verification_status or "OFFICIALLY_VERIFIED",
        is_saved=is_saved,
    )


# -------------------------------------------------------------------------
# 5. Saved Schemes (Bookmarks)
# -------------------------------------------------------------------------

@router.get("/user/saved", response_model=List[SavedSchemeOut])
async def list_user_saved_schemes(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves all schemes saved/bookmarked by the current user.
    """
    if not current_user:
        return []

    stmt = (
        select(SavedUserScheme)
        .options(selectinload(SavedUserScheme.scheme))
        .where(SavedUserScheme.user_id == current_user.id)
        .order_by(SavedUserScheme.saved_at.desc())
    )
    saved = (await db.execute(stmt)).scalars().all()
    return saved


@router.post("/{scheme_id}/save", status_code=status.HTTP_201_CREATED)
async def save_scheme_for_user(
    scheme_id: UUID,
    payload: Optional[SavedSchemeCreateIn] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Bookmarks a government scheme for the current user.
    """
    # Verify scheme exists
    s_stmt = select(GovernmentScheme).where(GovernmentScheme.id == scheme_id)
    scheme = (await db.execute(s_stmt)).scalar_one_or_none()
    if not scheme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Government scheme not found.",
        )

    # Check already saved
    exist_stmt = select(SavedUserScheme).where(
        and_(
            SavedUserScheme.user_id == current_user.id,
            SavedUserScheme.scheme_id == scheme_id,
        )
    )
    existing = (await db.execute(exist_stmt)).scalar_one_or_none()
    if existing:
        return {"status": "already_saved", "message": "Scheme is already saved in your bookmarks."}

    new_saved = SavedUserScheme(
        user_id=current_user.id,
        scheme_id=scheme_id,
        saved_at=datetime.now(timezone.utc),
        notes=payload.notes if payload else None,
    )
    db.add(new_saved)
    await db.commit()
    return {"status": "success", "message": "Scheme saved to your bookmarks."}


@router.delete("/{scheme_id}/save", status_code=status.HTTP_200_OK)
async def remove_saved_scheme(
    scheme_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Removes a scheme from the current user's bookmarks.
    """
    stmt = delete(SavedUserScheme).where(
        and_(
            SavedUserScheme.user_id == current_user.id,
            SavedUserScheme.scheme_id == scheme_id,
        )
    )
    result = await db.execute(stmt)
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved scheme not found.")
    return {"status": "success", "message": "Scheme removed from bookmarks."}


# -------------------------------------------------------------------------
# 6. Side-by-Side Scheme Comparison
# -------------------------------------------------------------------------

@router.post("/compare", response_model=CompareSchemesOut)
async def compare_government_schemes(
    payload: CompareSchemesIn,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns side-by-side comparative data for 1 to 5 selected government schemes.
    """
    stmt = select(GovernmentScheme).where(GovernmentScheme.id.in_(payload.scheme_ids))
    schemes = (await db.execute(stmt)).scalars().all()

    if not schemes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No matching schemes found.")

    out_schemes = []
    for s in schemes:
        docs = [
            RequiredDocumentOut(
                name_en=d["name_en"],
                name_ta=d["name_ta"],
                is_mandatory=d.get("is_mandatory", True),
                description_en=d.get("description_en"),
                description_ta=d.get("description_ta"),
            )
            for d in (s.required_documents or [])
        ]
        out_schemes.append(
            GovernmentSchemeDetailOut(
                id=s.id,
                slug=s.slug,
                name=s.name,
                name_ta=s.name_ta,
                short_description=s.short_description,
                short_description_ta=s.short_description_ta,
                detailed_description=s.detailed_description,
                detailed_description_ta=s.detailed_description_ta,
                department=s.department,
                department_ta=s.department_ta,
                level=s.level,
                state=s.state,
                districts=s.districts,
                category=s.category,
                target_beneficiaries=s.target_beneficiaries,
                target_beneficiaries_ta=s.target_beneficiaries_ta,
                benefit_type=s.benefit_type,
                benefit_amount_desc=s.benefit_amount_desc,
                benefit_amount_desc_ta=s.benefit_amount_desc_ta,
                benefit_frequency=s.benefit_frequency,
                eligibility_rules=s.eligibility_rules,
                required_documents=docs,
                application_mode=s.application_mode,
                application_process=s.application_process,
                application_process_ta=s.application_process_ta,
                official_portal_url=s.official_portal_url,
                official_source_url=s.official_source_url,
                is_active=s.is_active,
                application_status=s.application_status,
                last_verified_at=s.last_verified_at,
                verification_status=s.verification_status,
            )
        )

    comparison_fields = [
        {"key": "department", "label_en": "Department", "label_ta": "அரசுத் துறை"},
        {"key": "level", "label_en": "Government Level", "label_ta": "அரசு நிலை (மத்திய/மாநில)"},
        {"key": "benefit_amount_desc", "label_en": "Financial Benefit", "label_ta": "நிதி உதவி / சலுகை"},
        {"key": "benefit_frequency", "label_en": "Payment Frequency", "label_ta": "வழங்கும் முறை"},
        {"key": "application_mode", "label_en": "Application Mode", "label_ta": "விண்ணப்பிக்கும் முறை"},
        {"key": "official_portal_url", "label_en": "Official Portal", "label_ta": "அதிகாரப்பூர்வ தளம்"},
    ]

    return CompareSchemesOut(
        schemes=out_schemes,
        comparison_fields=comparison_fields,
    )


# -------------------------------------------------------------------------
# 7. Personalized Document Checklist Aggregator
# -------------------------------------------------------------------------

@router.post("/documents/checklist", response_model=DocumentChecklistOut)
async def generate_document_checklist(
    payload: DocumentChecklistIn,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates a unified, deduplicated document checklist across specified or saved schemes.
    Distinguishes mandatory documents from optional supporting documents.
    """
    scheme_ids = payload.scheme_ids
    if not scheme_ids:
        # Load user's saved schemes if logged in
        if current_user:
            saved_stmt = select(SavedUserScheme.scheme_id).where(SavedUserScheme.user_id == current_user.id)
            scheme_ids = list((await db.execute(saved_stmt)).scalars().all())

    if not scheme_ids:
        # Fallback to top schemes
        top_stmt = select(GovernmentScheme.id).limit(3)
        scheme_ids = list((await db.execute(top_stmt)).scalars().all())

    stmt = select(GovernmentScheme).where(GovernmentScheme.id.in_(scheme_ids))
    schemes = (await db.execute(stmt)).scalars().all()

    doc_map: Dict[str, Dict[str, Any]] = {}
    schemes_covered = []

    for s in schemes:
        schemes_covered.append({"id": str(s.id), "name": s.name, "name_ta": s.name_ta})
        for doc in (s.required_documents or []):
            name_en = doc["name_en"]
            if name_en not in doc_map:
                doc_map[name_en] = {
                    "name_en": name_en,
                    "name_ta": doc["name_ta"],
                    "is_mandatory": doc.get("is_mandatory", True),
                    "description_en": doc.get("description_en"),
                    "description_ta": doc.get("description_ta"),
                    "required_for_schemes": [s.name],
                    "required_for_schemes_ta": [s.name_ta],
                }
            else:
                if doc.get("is_mandatory", True):
                    doc_map[name_en]["is_mandatory"] = True
                if s.name not in doc_map[name_en]["required_for_schemes"]:
                    doc_map[name_en]["required_for_schemes"].append(s.name)
                    doc_map[name_en]["required_for_schemes_ta"].append(s.name_ta)

    mandatory = [d for d in doc_map.values() if d["is_mandatory"]]
    optional = [d for d in doc_map.values() if not d["is_mandatory"]]

    return DocumentChecklistOut(
        total_documents=len(doc_map),
        mandatory_documents=mandatory,
        optional_documents=optional,
        schemes_covered=schemes_covered,
    )


# -------------------------------------------------------------------------
# 8. Admin Management & Seed Synchronization
# -------------------------------------------------------------------------

@router.post("/admin/sync", status_code=status.HTTP_200_OK)
async def admin_sync_schemes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Administrative endpoint to sync and refresh verified government schemes.
    """
    if current_user.role not in ["ADMIN", "STAFF"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required to sync government schemes.",
        )

    seeded_count = await SchemeRecommendationEngine.seed_verified_schemes_if_empty(db)
    return {
        "status": "success",
        "message": f"Verified government schemes synchronized successfully. Total schemes: {seeded_count}",
    }
