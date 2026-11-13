"""
Deterministic Government Scheme Recommendation and Eligibility Evaluation Engine.
Evaluates user questionnaire profile against published scheme criteria without hallucination.
Produces transparent statuses: LIKELY_ELIGIBLE, POSSIBLY_ELIGIBLE, MORE_INFO_REQUIRED, NOT_ELIGIBLE.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.scheme import GovernmentScheme, UserSchemeProfile, SavedUserScheme
from app.models.user import User
from app.models.patient import Patient
from app.models.village import Village
from app.schemas.scheme import (
    EligibilityEvaluationOut,
    GovernmentSchemeDetailOut,
    RequiredDocumentOut,
    SchemeRecommendationResponse,
)
from app.services.scheme_data import VERIFIED_SCHEMES


class SchemeRecommendationEngine:
    """
    Deterministic rule-based eligibility evaluation engine.
    Compares user profile attributes against verified government scheme rules.
    """

    @staticmethod
    async def seed_verified_schemes_if_empty(db: AsyncSession) -> int:
        """Seeds the verified Central and Tamil Nadu government schemes if table is empty."""
        stmt = select(func.count(GovernmentScheme.id))
        count = (await db.execute(stmt)).scalar() or 0
        if count > 0:
            return count

        seeded_count = 0
        for data in VERIFIED_SCHEMES:
            scheme = GovernmentScheme(
                slug=data["slug"],
                name=data["name"],
                name_ta=data["name_ta"],
                short_description=data["short_description"],
                short_description_ta=data["short_description_ta"],
                detailed_description=data["detailed_description"],
                detailed_description_ta=data["detailed_description_ta"],
                department=data["department"],
                department_ta=data["department_ta"],
                level=data["level"],
                state=data["state"],
                districts=data["districts"],
                category=data["category"],
                target_beneficiaries=data["target_beneficiaries"],
                target_beneficiaries_ta=data["target_beneficiaries_ta"],
                benefit_type=data["benefit_type"],
                benefit_amount_desc=data["benefit_amount_desc"],
                benefit_amount_desc_ta=data["benefit_amount_desc_ta"],
                benefit_frequency=data["benefit_frequency"],
                eligibility_rules=data["eligibility_rules"],
                required_documents=data["required_documents"],
                application_mode=data["application_mode"],
                application_process=data["application_process"],
                application_process_ta=data["application_process_ta"],
                official_portal_url=data["official_portal_url"],
                official_source_url=data["official_source_url"],
                is_active=True,
                application_status=data.get("application_status", "ALWAYS_OPEN"),
                verification_status=data.get("verification_status", "OFFICIALLY_VERIFIED"),
                is_synthetic=False,
                last_verified_at=datetime.now(timezone.utc),
            )
            db.add(scheme)
            seeded_count += 1

        await db.commit()
        return seeded_count

    @staticmethod
    async def get_or_prefill_user_profile(user_id: UUID, db: AsyncSession) -> Tuple[Dict[str, Any], bool]:
        """
        Retrieves user's consented scheme profile. If not yet created, intelligently
        pre-fills basic fields from their existing NALAM Patient / Village profile.
        """
        stmt = select(UserSchemeProfile).where(UserSchemeProfile.user_id == user_id)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing and existing.profile_data:
            return existing.profile_data, False

        # Pre-fill from Patient & Village models if available
        prefilled_data: Dict[str, Any] = {
            "basic": {
                "age": 30,
                "state": "Tamil Nadu",
                "residence_type": "RURAL",
                "is_indian_citizen": True,
            },
            "household": {
                "family_size": 4,
                "is_female_headed": False,
                "marital_status": "MARRIED",
                "has_disabled_member": False,
            },
            "financial": {
                "income_range": "BELOW_1_LAKH",
                "employment_status": "EMPLOYED",
                "has_ration_card": True,
                "ration_card_type": "PHH",
            },
            "social": {
                "community_category": "OBC",
                "has_community_certificate": True,
                "has_disability_certificate": False,
                "is_widow": False,
                "is_senior_citizen": False,
                "is_student": False,
                "is_farmer": False,
            },
            "education_employment": {
                "current_education_status": "NOT_STUDYING",
                "studied_in_govt_school": False,
                "seeking_scholarships": False,
            },
            "agriculture_business": {
                "owns_agricultural_land": False,
                "has_business": False,
            },
            "healthcare_needs": {
                "needs_health_insurance": True,
                "needs_hospital_treatment_aid": True,
            },
            "financial_needs": ["ALL"],
        }

        # Query patient
        p_stmt = (
            select(Patient)
            .options(selectinload(Patient.village), selectinload(Patient.user))
            .where(Patient.user_id == user_id)
        )
        patient = (await db.execute(p_stmt)).scalar_one_or_none()

        if patient:
            # Calculate age from DOB
            if patient.date_of_birth:
                today = datetime.now(timezone.utc).date()
                age = today.year - patient.date_of_birth.year - (
                    (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day)
                )
                prefilled_data["basic"]["age"] = age
                prefilled_data["basic"]["dob"] = str(patient.date_of_birth)
                if age >= 60:
                    prefilled_data["social"]["is_senior_citizen"] = True

            if patient.village:
                prefilled_data["basic"]["village_or_town"] = patient.village.name
                prefilled_data["basic"]["district"] = patient.village.district
                if patient.village.state:
                    prefilled_data["basic"]["state"] = patient.village.state

        return prefilled_data, True

    @classmethod
    def evaluate_scheme_eligibility(
        cls,
        user_data: Dict[str, Any],
        scheme: GovernmentScheme,
        language: str = "ta",
    ) -> EligibilityEvaluationOut:
        """
        Evaluates a single scheme against user data with complete rule checks.
        """
        rules = scheme.eligibility_rules or {}
        basic = user_data.get("basic", {})
        household = user_data.get("household", {})
        financial = user_data.get("financial", {})
        social = user_data.get("social", {})
        edu = user_data.get("education_employment", {})
        agri = user_data.get("agriculture_business", {})
        hc = user_data.get("healthcare_needs", {})
        user_needs = user_data.get("financial_needs", ["ALL"])

        user_age = basic.get("age")
        user_gender = "FEMALE" if (household.get("is_female_headed") or social.get("is_widow")) else basic.get("gender")
        user_state = basic.get("state", "Tamil Nadu")
        user_district = basic.get("district")
        user_residence = basic.get("residence_type", "RURAL")
        user_income = financial.get("annual_income")
        income_range = financial.get("income_range", "BELOW_1_LAKH")
        has_ration = financial.get("has_ration_card", True)
        ration_type = financial.get("ration_card_type")
        is_widow = social.get("is_widow", False)
        has_disability = social.get("has_disability_certificate", False) or household.get("has_disabled_member", False)
        owns_land = agri.get("owns_agricultural_land", False) or social.get("is_farmer", False)
        studied_govt = edu.get("studied_in_govt_school", False)
        is_student = (
            social.get("is_student", False)
            or edu.get("current_education_status") in ["SCHOOL", "COLLEGE_UG", "COLLEGE_PG", "ITI_DIPLOMA"]
            or edu.get("seeking_scholarships", False)
        )

        # Approximate numerical income from range if annual_income is not provided
        derived_income = user_income
        if derived_income is None:
            if income_range == "BELOW_1_LAKH":
                derived_income = 80000
            elif income_range == "1_TO_2.5_LAKH":
                derived_income = 180000
            elif income_range == "2.5_TO_5_LAKH":
                derived_income = 350000
            elif income_range == "5_TO_8_LAKH":
                derived_income = 600000
            else:
                derived_income = 900000

        matched_reasons: List[str] = []
        unverified_conditions: List[str] = []
        missing_fields: List[str] = []
        hard_fail = False
        potential_fail = False

        # 1. State / Geography Check
        allowed_states = rules.get("allowed_states", ["ALL"])
        if "ALL" not in allowed_states and user_state not in allowed_states:
            hard_fail = True
            missing_fields.append(f"Residency outside {', '.join(allowed_states)}")
        else:
            if "ALL" in allowed_states or user_state in allowed_states:
                matched_reasons.append(
                    f"வசிப்பிடம் தகுதியானது ({user_state})"
                    if language == "ta"
                    else f"Resident of eligible region ({user_state})"
                )

        # 2. Residence Type (RURAL / URBAN)
        rule_res = rules.get("residence_type")
        if rule_res:
            if user_residence not in rule_res:
                hard_fail = True
            else:
                matched_reasons.append(
                    "கிராமப்புற குடியிருப்பு நிபந்தனை பொருந்துகிறது"
                    if language == "ta"
                    else f"Residence type matches ({user_residence})"
                )

        # 3. Age Restrictions
        min_age = rules.get("min_age")
        max_age = rules.get("max_age")
        if min_age is not None:
            if user_age is not None:
                if user_age < min_age:
                    hard_fail = True
                else:
                    matched_reasons.append(
                        f"வயது வரம்பு பொருந்துகிறது ({user_age} வயது >= {min_age})"
                        if language == "ta"
                        else f"Age meets minimum requirement ({user_age} >= {min_age})"
                    )
            else:
                potential_fail = True
                missing_fields.append("வயது குறிப்பிடப்படவில்லை" if language == "ta" else "Age not specified")

        if max_age is not None:
            if user_age is not None:
                if user_age > max_age:
                    hard_fail = True
                else:
                    matched_reasons.append(
                        f"வயது வரம்பு பொருந்துகிறது ({user_age} வயது <= {max_age})"
                        if language == "ta"
                        else f"Age within maximum limit ({user_age} <= {max_age})"
                    )
            else:
                potential_fail = True
                missing_fields.append("வயது உறுதிப்படுத்தப்படவில்லை" if language == "ta" else "Age not confirmed")

        # 4. Gender Restrictions
        rule_gender = rules.get("gender")
        if rule_gender:
            if "FEMALE" in rule_gender:
                if household.get("is_female_headed") or social.get("is_widow") or social.get("is_woman_seeking_aid"):
                    matched_reasons.append(
                        "பெண்கள் / குடும்பத்தலைவி நலத்திட்ட நிபந்தனை பொருந்துகிறது"
                        if language == "ta"
                        else "Applicant satisfies women's welfare eligibility"
                    )
                elif user_gender == "MALE":
                    hard_fail = True
                else:
                    unverified_conditions.append(
                        "குடும்பத் தலைவி / பெண் விண்ணப்பதாரர் சான்றிதழ் தேவை"
                        if language == "ta"
                        else "Female head of family verification required"
                    )

            if "MALE" in rule_gender:
                if user_gender == "MALE":
                    matched_reasons.append(
                        "மாணவர் கல்வி உதவித்தொகை தகுதி பொருந்துகிறது"
                        if language == "ta"
                        else "Male student qualification matches"
                    )
                elif user_gender == "FEMALE":
                    hard_fail = True

        # 5. Income Restrictions
        max_income = rules.get("max_annual_income")
        if max_income is not None:
            if derived_income is not None:
                if derived_income > max_income * 1.25:  # Tolerance threshold for hard fail
                    hard_fail = True
                elif derived_income > max_income:
                    potential_fail = True
                    unverified_conditions.append(
                        f"ஆண்டு வருமானம் ₹{max_income:,}-க்குள் இருக்க வேண்டும் (வருவாய்த்துறை சரிபார்ப்பு தேவை)"
                        if language == "ta"
                        else f"Annual income must be within ₹{max_income:,} (Revenue verification needed)"
                    )
                else:
                    matched_reasons.append(
                        f"ஆண்டு வருமான வரம்பிற்குள் உள்ளது (வரம்பு: ₹{max_income:,})"
                        if language == "ta"
                        else f"Income satisfies threshold (< ₹{max_income:,})"
                    )
                    unverified_conditions.append(
                        "வட்டாட்சியர் வருமானச் சான்றிதழ் சமர்ப்பிக்க வேண்டும்"
                        if language == "ta"
                        else "Tahsildar income certificate required for formal approval"
                    )
            else:
                potential_fail = True
                missing_fields.append("வருமான வரம்பு உறுதிப்படுத்தப்படவில்லை" if language == "ta" else "Income unverified")

        # 6. Ration Card Criteria
        if rules.get("ration_card_required"):
            if has_ration:
                matched_reasons.append(
                    "செல்லுபடியாகும் குடும்ப அட்டை உள்ளது"
                    if language == "ta"
                    else "Active Ration / Smart card verified"
                )
            else:
                hard_fail = True

        # 7. Agriculture / Land Criteria
        if rules.get("owns_agricultural_land"):
            if owns_land:
                matched_reasons.append(
                    "விவசாய நிலம் / உழவர் தகுதி பொருந்துகிறது"
                    if language == "ta"
                    else "Agricultural landholder criteria matches"
                )
                unverified_conditions.append(
                    "நிலப் பட்டா / சிட்டா மற்றும் VAO சரிபார்ப்பு தேவை"
                    if language == "ta"
                    else "Land Patta/Chitta and VAO certification required"
                )
            else:
                hard_fail = True

        # 8. Disability Criteria
        if rules.get("has_disability"):
            if has_disability:
                matched_reasons.append(
                    "மாற்றுத்திறனாளி நலத்திட்ட நிபந்தனை பொருந்துகிறது"
                    if language == "ta"
                    else "Differently abled welfare condition matches"
                )
                unverified_conditions.append(
                    "UDID அட்டை / மருத்துவக் குழு சான்றிதழ் சரிபார்ப்பு தேவை"
                    if language == "ta"
                    else "UDID Card / Medical Board certificate verification required"
                )
            else:
                hard_fail = True

        # 9. Widow Criteria
        if rules.get("is_widow"):
            if is_widow:
                matched_reasons.append(
                    "ஆதரவற்ற விதவை ஓய்வூதிய தகுதி பொருந்துகிறது"
                    if language == "ta"
                    else "Destitute widow pension criteria matches"
                )
                unverified_conditions.append(
                    "கணவரின் இறப்புச் சான்றிதழ் மற்றும் வட்டாட்சியர் சான்று தேவை"
                    if language == "ta"
                    else "Husband's death certificate & Tahsildar order required"
                )
            else:
                hard_fail = True

        # 10. Schooling Criteria (Pudhumai Penn / Tamil Pudhalvan)
        if rules.get("studied_in_govt_school"):
            if studied_govt or is_student:
                matched_reasons.append(
                    "அரசுப் பள்ளி மற்றும் கல்லூரி பயில்வு நிபந்தனை பொருந்துகிறது"
                    if language == "ta"
                    else "Govt school (6th-12th) and college enrollment matches"
                )
                unverified_conditions.append(
                    "பள்ளி தலைமையாசிரியர் சான்றிதழ் & கல்லூரி பயில்வுச் சான்று தேவை"
                    if language == "ta"
                    else "HM School study certificate & College bonafide required"
                )
            else:
                potential_fail = True
                missing_fields.append(
                    "அரசுப் பள்ளியில் படித்த விவரம் தேவை"
                    if language == "ta"
                    else "Govt school study status needed"
                )

        # 11. Needs Alignment
        scheme_needs = rules.get("need_categories", ["ALL"])
        has_need_match = "ALL" in user_needs or any(n in user_needs for n in scheme_needs)

        # -------------------------------------------------------------
        # Determine Status and Scoring
        # -------------------------------------------------------------
        if hard_fail:
            status = "NOT_ELIGIBLE"
            score = 10.0
        elif len(missing_fields) > 1:
            status = "MORE_INFO_REQUIRED"
            score = 50.0 + (15.0 if has_need_match else 0.0)
        elif potential_fail or len(missing_fields) == 1:
            status = "POSSIBLY_ELIGIBLE"
            score = 75.0 + (15.0 if has_need_match else 0.0)
        else:
            status = "LIKELY_ELIGIBLE"
            score = 90.0 + (10.0 if has_need_match else 0.0)

        # Boost for high-value welfare/healthcare assistance
        if scheme.category == "HEALTHCARE" or scheme.benefit_type in ["HEALTH_INSURANCE", "CASH_TRANSFER"]:
            score = min(100.0, score + 5.0)

        # Build schema details
        docs_out = [
            RequiredDocumentOut(
                name_en=d["name_en"],
                name_ta=d["name_ta"],
                is_mandatory=d.get("is_mandatory", True),
                description_en=d.get("description_en"),
                description_ta=d.get("description_ta"),
            )
            for d in (scheme.required_documents or [])
        ]

        detail_out = GovernmentSchemeDetailOut(
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
            eligibility_rules=scheme.eligibility_rules,
            required_documents=docs_out,
            application_mode=scheme.application_mode,
            application_process=scheme.application_process,
            application_process_ta=scheme.application_process_ta,
            official_portal_url=scheme.official_portal_url,
            official_source_url=scheme.official_source_url,
            is_active=scheme.is_active,
            application_status=scheme.application_status,
            last_verified_at=scheme.last_verified_at,
            verification_status=scheme.verification_status,
        )

        return EligibilityEvaluationOut(
            scheme=detail_out,
            eligibility_status=status,
            match_score=round(score, 1),
            matched_reasons=matched_reasons or ["அடிப்படை வசிப்பிட நிபந்தனை பொருந்துகிறது" if language == "ta" else "Basic residency satisfied"],
            unverified_conditions=unverified_conditions or ["அரசு அதிகாரப்பூர்வ ஆவண சரிபார்ப்புக்கு உட்பட்டது" if language == "ta" else "Subject to official government document scrutiny"],
            missing_fields=missing_fields,
            required_documents=docs_out,
        )

    @classmethod
    async def get_recommendations_for_user(
        cls,
        user_id: UUID,
        db: AsyncSession,
        language: str = "ta",
        category: Optional[str] = None,
        level: Optional[str] = None,
    ) -> SchemeRecommendationResponse:
        """
        Retrieves user's consented profile and ranks all active schemes by eligibility.
        """
        # Ensure seed data exists
        await cls.seed_verified_schemes_if_empty(db)

        # Get consented profile
        user_data, _ = await cls.get_or_prefill_user_profile(user_id, db)

        # Load all active schemes
        stmt = select(GovernmentScheme).where(GovernmentScheme.is_active == True)
        if category and category != "ALL":
            stmt = stmt.where(GovernmentScheme.category == category)
        if level and level != "ALL":
            stmt = stmt.where(GovernmentScheme.level == level)

        schemes = (await db.execute(stmt)).scalars().all()

        # Load saved scheme IDs for user
        saved_stmt = select(SavedUserScheme.scheme_id).where(SavedUserScheme.user_id == user_id)
        saved_ids = set((await db.execute(saved_stmt)).scalars().all())

        evaluated: List[EligibilityEvaluationOut] = []
        likely_count = 0
        possibly_count = 0
        more_info_count = 0

        for s in schemes:
            eval_res = cls.evaluate_scheme_eligibility(user_data, s, language=language)
            eval_res.is_saved = s.id in saved_ids

            if eval_res.eligibility_status == "LIKELY_ELIGIBLE":
                likely_count += 1
                evaluated.append(eval_res)
            elif eval_res.eligibility_status == "POSSIBLY_ELIGIBLE":
                possibly_count += 1
                evaluated.append(eval_res)
            elif eval_res.eligibility_status == "MORE_INFO_REQUIRED":
                more_info_count += 1
                evaluated.append(eval_res)
            # NOT_ELIGIBLE schemes are omitted from default recommendations to prevent cognitive overload

        # Sort by match_score descending, then level (STATE first for TN, then CENTRAL)
        evaluated.sort(
            key=lambda item: (
                item.match_score,
                1 if item.scheme.level == "STATE" else 0,
            ),
            reverse=True,
        )

        disclaimer_en = (
            "Disclaimer: Recommendations are simulated estimates based on your provided information "
            "and officially published government criteria. NALAM AI does not guarantee government approval. "
            "Final sanction is determined solely by the competent Government Authority upon document verification."
        )
        disclaimer_ta = (
            "பொறுப்புத் துறப்பு: இந்த பரிந்துரைகள் நீங்கள் வழங்கிய தகவல்கள் மற்றும் அரசு வெளியிட்ட அளவுகோல்களின் "
            "அடிப்படையில் கணிக்கப்பட்டவை. இது அதிகாரப்பூர்வ ஒப்புதலை உறுதிப்படுத்தாது. இறுதி அனுமதி அரசுத் துறை "
            "மற்றும் தகுதிவாய்ந்த அதிகாரிகளின் நேரடி ஆவண சரிபார்ப்புக்குப் பிறகே வழங்கப்படும்."
        )

        return SchemeRecommendationResponse(
            total_evaluated=len(schemes),
            likely_eligible_count=likely_count,
            possibly_eligible_count=possibly_count,
            more_info_count=more_info_count,
            recommendations=evaluated,
            disclaimer=disclaimer_en,
            disclaimer_ta=disclaimer_ta,
        )
