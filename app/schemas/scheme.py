"""
Pydantic schemas for NALAM Scheme Finder — Government Schemes & Financial Benefits.
Supports multi-step questionnaire validation, deterministic recommendations,
saved schemes, comparisons, and document checklists.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


# -------------------------------------------------------------------------
# Questionnaire Input Schemas (Steps 1 to 8)
# -------------------------------------------------------------------------

class BasicPersonalInfo(BaseModel):
    age: Optional[int] = Field(None, ge=0, le=120)
    dob: Optional[str] = None
    state: str = "Tamil Nadu"
    district: Optional[str] = None
    village_or_town: Optional[str] = None
    residence_type: str = "RURAL"  # RURAL, URBAN
    is_indian_citizen: bool = True


class HouseholdInfo(BaseModel):
    family_size: Optional[int] = Field(None, ge=1, le=30)
    earning_members: Optional[int] = Field(None, ge=0, le=20)
    dependents: Optional[int] = Field(None, ge=0, le=25)
    children_count: Optional[int] = Field(None, ge=0, le=15)
    senior_citizens_count: Optional[int] = Field(None, ge=0, le=10)
    is_female_headed: bool = False
    marital_status: str = "MARRIED"  # SINGLE, MARRIED, WIDOWED, DIVORCED, DESERTED
    has_disabled_member: bool = False


class FinancialInfo(BaseModel):
    annual_income: Optional[int] = Field(None, ge=0)
    income_range: str = "BELOW_1_LAKH"  # BELOW_1_LAKH, 1_TO_2.5_LAKH, 2.5_TO_5_LAKH, 5_TO_8_LAKH, ABOVE_8_LAKH
    income_source: Optional[str] = None  # AGRICULTURE, DAILY_WAGE, SALARIED, BUSINESS, PENSION, UNEMPLOYED
    employment_status: str = "EMPLOYED"  # EMPLOYED, UNEMPLOYED, SELF_EMPLOYED, DAILY_WAGE, PENSIONER
    has_ration_card: bool = True
    ration_card_type: Optional[str] = "PHH"  # PHH, PHH_AAY, NPHH, NONE
    existing_benefits: List[str] = Field(default_factory=list)


class SocialEligibilityInfo(BaseModel):
    community_category: Optional[str] = "OBC"  # SC, ST, OBC, MBC, GENERAL
    has_community_certificate: bool = True
    has_disability_certificate: bool = False
    disability_percentage: Optional[int] = Field(None, ge=0, le=100)
    is_widow: bool = False
    is_senior_citizen: bool = False
    is_student: bool = False
    is_woman_seeking_aid: bool = False
    is_farmer: bool = False


class EducationEmploymentInfo(BaseModel):
    highest_qualification: Optional[str] = None  # BELOW_10TH, 10TH_PASS, 12TH_PASS, ITI_DIPLOMA, GRADUATE, POST_GRADUATE
    current_education_status: Optional[str] = "NOT_STUDYING"  # SCHOOL, COLLEGE_UG, COLLEGE_PG, ITI_DIPLOMA, NOT_STUDYING
    studied_in_govt_school: bool = False  # Relevant for Pudhumai Penn / Tamil Pudhalvan
    seeking_scholarships: bool = False
    seeking_employment: bool = False
    seeking_skill_development: bool = False
    interested_in_business: bool = False
    is_registered_welfare_board: bool = False
    welfare_board_name: Optional[str] = None


class AgricultureBusinessInfo(BaseModel):
    owns_agricultural_land: bool = False
    land_acres: Optional[float] = Field(None, ge=0.0)
    land_type: Optional[str] = "WETLAND"  # WETLAND, DRYLAND
    farmer_category: Optional[str] = "SMALL_MARGINAL"  # MARGINAL, SMALL, LARGE, TENANT, AGRICULTURAL_LABORER
    farming_type: Optional[str] = "CROPS"  # CROPS, DAIRY, POULTRY, MIXED
    has_farmer_card: bool = False
    has_business: bool = False
    business_type: Optional[str] = None
    is_business_registered: bool = False
    business_scale: Optional[str] = "MICRO"  # MICRO, SMALL, MEDIUM


class HealthcareNeedsInfo(BaseModel):
    needs_health_insurance: bool = True
    needs_hospital_treatment_aid: bool = False
    needs_maternal_child_care: bool = False
    needs_disability_support: bool = False
    needs_senior_care: bool = False
    needs_medicine_assistance: bool = False
    needs_nutrition_support: bool = False
    needs_maternity_benefits: bool = False


class UserProfileData(BaseModel):
    basic: BasicPersonalInfo = Field(default_factory=BasicPersonalInfo)
    household: HouseholdInfo = Field(default_factory=HouseholdInfo)
    financial: FinancialInfo = Field(default_factory=FinancialInfo)
    social: SocialEligibilityInfo = Field(default_factory=SocialEligibilityInfo)
    education_employment: EducationEmploymentInfo = Field(default_factory=EducationEmploymentInfo)
    agriculture_business: AgricultureBusinessInfo = Field(default_factory=AgricultureBusinessInfo)
    healthcare_needs: HealthcareNeedsInfo = Field(default_factory=HealthcareNeedsInfo)
    financial_needs: List[str] = Field(default_factory=lambda: ["ALL"])


class UserSchemeProfileIn(BaseModel):
    consent_given: bool = True
    step_progress: int = Field(1, ge=1, le=8)
    profile_data: Dict[str, Any] = Field(default_factory=dict)


class UserSchemeProfileOut(BaseModel):
    id: UUID
    user_id: UUID
    consent_given: bool
    consent_timestamp: Optional[datetime] = None
    step_progress: int
    profile_data: Dict[str, Any]
    prefilled_from_profile: bool = False

    model_config = {"from_attributes": True}


# -------------------------------------------------------------------------
# Government Scheme Response Schemas
# -------------------------------------------------------------------------

class RequiredDocumentOut(BaseModel):
    name_en: str
    name_ta: str
    is_mandatory: bool = True
    description_en: Optional[str] = None
    description_ta: Optional[str] = None


class GovernmentSchemeBase(BaseModel):
    id: UUID
    slug: str
    name: str
    name_ta: str
    short_description: str
    short_description_ta: str
    department: str
    department_ta: str
    level: str  # CENTRAL, STATE, DISTRICT, LOCAL
    state: str
    districts: List[str]
    category: str
    benefit_type: str
    benefit_amount_desc: str
    benefit_amount_desc_ta: str
    benefit_frequency: str
    official_portal_url: str
    official_source_url: str
    is_active: bool
    application_status: str
    last_verified_at: datetime
    verification_status: str

    model_config = {"from_attributes": True}


class GovernmentSchemeDetailOut(GovernmentSchemeBase):
    detailed_description: str
    detailed_description_ta: str
    target_beneficiaries: List[str]
    target_beneficiaries_ta: List[str]
    eligibility_rules: Dict[str, Any]
    required_documents: List[RequiredDocumentOut]
    application_mode: str
    application_process: str
    application_process_ta: str
    is_saved: bool = False


# -------------------------------------------------------------------------
# Eligibility Assessment & Recommendations
# -------------------------------------------------------------------------

class EligibilityEvaluationOut(BaseModel):
    scheme: GovernmentSchemeDetailOut
    eligibility_status: str  # LIKELY_ELIGIBLE, POSSIBLY_ELIGIBLE, MORE_INFO_REQUIRED, NOT_ELIGIBLE
    match_score: float
    matched_reasons: List[str]
    unverified_conditions: List[str]
    missing_fields: List[str]
    required_documents: List[RequiredDocumentOut]
    is_saved: bool = False


class SchemeRecommendationResponse(BaseModel):
    total_evaluated: int
    likely_eligible_count: int
    possibly_eligible_count: int
    more_info_count: int
    recommendations: List[EligibilityEvaluationOut]
    disclaimer: str
    disclaimer_ta: str


# -------------------------------------------------------------------------
# Saved Schemes, Comparison, and Checklists
# -------------------------------------------------------------------------

class SavedSchemeCreateIn(BaseModel):
    notes: Optional[str] = None


class SavedSchemeOut(BaseModel):
    id: UUID
    scheme_id: UUID
    saved_at: datetime
    notes: Optional[str] = None
    scheme: GovernmentSchemeBase

    model_config = {"from_attributes": True}


class CompareSchemesIn(BaseModel):
    scheme_ids: List[UUID] = Field(..., min_length=1, max_length=5)


class CompareSchemesOut(BaseModel):
    schemes: List[GovernmentSchemeDetailOut]
    comparison_fields: List[Dict[str, Any]]


class DocumentChecklistIn(BaseModel):
    scheme_ids: Optional[List[UUID]] = None  # None = use saved schemes


class DocumentChecklistOut(BaseModel):
    total_documents: int
    mandatory_documents: List[Dict[str, Any]]
    optional_documents: List[Dict[str, Any]]
    schemes_covered: List[Dict[str, str]]


# -------------------------------------------------------------------------
# Dynamic Questionnaire Matching & Service Health Schemas
# -------------------------------------------------------------------------

class QuestionnaireAnswersIn(BaseModel):
    # Step 1: Location
    state: Optional[str] = "Tamil Nadu"
    district: Optional[str] = None
    pincode: Optional[str] = None
    town_or_village: Optional[str] = None

    # Step 2: Personal profile
    age: Optional[int] = Field(None, ge=0, le=120)
    age_range: Optional[str] = None
    gender: Optional[str] = None  # FEMALE, MALE, TRANSGENDER, PREFER_NOT_TO_SAY
    residence: Optional[str] = "RURAL"  # RURAL, URBAN

    # Step 3: Household & income
    annual_income: Optional[int] = Field(None, ge=0)
    income_range: Optional[str] = "BELOW_72K"  # BELOW_72K, 72K_TO_120K, 120K_TO_250K, 250K_TO_500K, ABOVE_500K
    family_size: Optional[int] = Field(None, ge=1, le=30)
    is_woman_head_of_household: Optional[bool] = False
    is_head_of_household: Optional[bool] = False
    ration_card_type: Optional[str] = "PHH"  # PHH, PHH_AAY, NPHH, NPHH_S, NONE, UNKNOWN

    # Step 4: Social eligibility
    caste_category: Optional[str] = None  # SC, ST, MBC, BC, GENERAL, PREFER_NOT_TO_SAY
    is_differently_abled: Optional[bool] = False
    disability_percentage: Optional[int] = Field(None, ge=0, le=100)
    special_circumstances: Optional[List[str]] = Field(default_factory=list)

    # Step 5: Employment & education
    employment_status: Optional[str] = None  # EMPLOYED, UNEMPLOYED, SELF_EMPLOYED, DAILY_WAGE, STUDENT, RETIRED
    student_status: Optional[str] = None  # SCHOOL, HIGHER_SECONDARY, GOVT_COLLEGE, PRIVATE_COLLEGE, ITI_DIPLOMA, NOT_STUDYING
    studied_in_govt_school: Optional[bool] = False  # Tamil Nadu Govt school (6th to 12th)
    occupation: Optional[str] = None
    education_level: Optional[str] = None

    # Step 6: Health & family circumstances
    pregnancy_status: Optional[str] = "NONE"  # PREGNANT, LACTATING, CHILD_UNDER_2, NONE
    is_senior_citizen: Optional[bool] = False
    healthcare_needs: Optional[List[str]] = Field(default_factory=list)  # tertiary_care, chronic_disease, assistive_devices
    is_farmer: Optional[bool] = False
    landholding_acres: Optional[float] = Field(None, ge=0.0)

    # Step 7: Existing benefits & desired welfare
    existing_benefits: Optional[List[str]] = Field(default_factory=list)
    desired_assistance: Optional[List[str]] = Field(default_factory=list)

    # Freeform / raw answers map
    profile_data: Optional[Dict[str, Any]] = None
    language: Optional[str] = "ta"


class SchemeMatchItemOut(BaseModel):
    scheme: GovernmentSchemeDetailOut
    match_status: str  # LIKELY_MATCH, MORE_INFO_NEEDED, NOT_MATCHING
    match_status_label_en: str
    match_status_label_ta: str
    match_score: float
    reasons: List[str]
    missing_information: List[str]
    unmet_criteria: List[str]
    required_documents: List[RequiredDocumentOut]
    official_source_url: str
    official_portal_url: str
    last_verified_date: str
    application_status: str
    is_saved: bool = False


class SchemeMatchResponse(BaseModel):
    total_evaluated: int
    likely_matches_count: int
    more_info_needed_count: int
    not_matching_count: int
    likely_matches: List[SchemeMatchItemOut]
    more_info_needed: List[SchemeMatchItemOut]
    not_matching: List[SchemeMatchItemOut]
    all_results: List[SchemeMatchItemOut]
    disclaimer_en: str
    disclaimer_ta: str
    evaluated_at: datetime


class SchemeHealthResponse(BaseModel):
    status: str
    service: str
    database: str
    total_schemes: int
    sources: List[str]
    last_catalog_verification: str
    timestamp: datetime

