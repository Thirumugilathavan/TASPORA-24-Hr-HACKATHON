from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class FacilityType(str, Enum):
    PHC = "PHC"
    CHC = "CHC"
    HOSPITAL = "HOSPITAL"
    PHARMACY = "PHARMACY"
    SCE = "SCE"  # Health Sub-Centre
    THO = "THO"  # Taluk Hospital
    DHO = "DHO"  # District Hospital
    SUB_CENTRE = "SUB_CENTRE"
    UPHC = "UPHC"
    MATERNITY_HOME = "MATERNITY_HOME"


class FacilityServiceResponse(BaseModel):
    id: UUID
    service_name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FacilitySpecialtyResponse(BaseModel):
    id: UUID
    specialty_name: str
    is_verified: bool = True
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FacilitySourceResponse(BaseModel):
    id: UUID
    source_name: str
    source_url: str
    source_type: str
    date_collected: str
    verification_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FacilityAppointmentConfigResponse(BaseModel):
    id: UUID
    booking_method: str
    booking_url: Optional[str] = None
    booking_phone: Optional[str] = None
    instructions_en: Optional[str] = None
    instructions_ta: Optional[str] = None
    requires_registration: bool = True
    lead_time_days: int = 0
    is_verified: bool = True

    model_config = ConfigDict(from_attributes=True)


class DoctorSummary(BaseModel):
    id: UUID
    name: str
    specialization: str
    qualification: Optional[str] = None
    contact_phone: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FacilityBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    facility_type: str
    address: str = Field(..., min_length=1, max_length=500)
    village_id: Optional[UUID] = None
    district: Optional[str] = None
    state: Optional[str] = "Tamil Nadu"
    subdistrict: Optional[str] = None
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in range [-90.0, 90.0]")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in range [-180.0, 180.0]")
    ownership: Optional[str] = "Government"
    source: Optional[str] = "nic"
    source_id: Optional[str] = None
    contact_details: Optional[Dict[str, Any]] = None

    # Verified Extended Fields
    alternate_names: Optional[List[str]] = None
    facility_category: Optional[str] = "HOSPITAL"
    health_unit_district: Optional[str] = None
    block: Optional[str] = None
    locality: Optional[str] = None
    pincode: Optional[str] = None
    geographic_verification_status: Optional[str] = "VERIFIED_COORDINATES"
    official_phone: Optional[str] = None
    official_email: Optional[str] = None
    official_website: Optional[str] = None
    emergency_contact: Optional[str] = None
    opd_available: Optional[bool] = True
    opening_hours: Optional[str] = None
    emergency_services: Optional[bool] = False
    ambulance_available: Optional[bool] = False
    maternity_services: Optional[bool] = False
    pharmacy_available: Optional[bool] = True
    laboratory_services: Optional[bool] = True
    imaging_services: Optional[bool] = False
    specialties: Optional[List[str]] = None
    appointment_booking_method: Optional[str] = "WALK_IN_ONLY"
    online_booking_url: Optional[str] = None
    official_source_url: Optional[str] = None
    source_type: Optional[str] = None
    date_collected: Optional[str] = None
    last_verified_date: Optional[str] = None
    verification_status: Optional[str] = "VERIFIED_OFFICIAL"
    data_completeness_score: Optional[float] = 0.0

    @field_validator("facility_type")
    @classmethod
    def validate_facility_type(cls, v: str) -> str:
        v_upper = v.strip().upper()
        allowed = {t.value for t in FacilityType}
        if v_upper not in allowed:
            # Allow common category variations
            return v_upper
        return v_upper

    @field_validator("name", "address")
    @classmethod
    def strip_and_validate_non_empty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Field cannot be empty or whitespace only")
        return s


class FacilityCreate(FacilityBase):
    village_id: Optional[UUID] = Field(None, description="Village UUID for facility creation")
    services: Optional[List[str]] = []

    @field_validator("services")
    @classmethod
    def validate_services(cls, v: Optional[List[str]]) -> List[str]:
        if not v:
            return []
        cleaned = [s.strip() for s in v if s and s.strip()]
        return cleaned


class FacilityResponse(FacilityBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class NearbyFacilityResponse(FacilityResponse):
    distance_km: float = Field(..., description="Calculated straight-line geographic distance in kilometres")
    unverified_availability: bool = Field(True, description="Flag indicating availability data is not verified")
    directions_url: Optional[str] = Field(None, description="Google Maps navigation link")


class NearbyFacilityList(BaseModel):
    items: List[NearbyFacilityResponse]
    total: int
    resolved_location: Dict[str, Any]
    radius_km: float
    skip: int = 0
    limit: int = 20
    has_more: bool = False


class FacilityDetailResponse(FacilityBase):
    id: UUID
    services: List[FacilityServiceResponse] = []
    specialties_rel: List[FacilitySpecialtyResponse] = []
    sources_rel: List[FacilitySourceResponse] = []
    appointment_config: Optional[FacilityAppointmentConfigResponse] = None
    doctors: List[DoctorSummary] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
