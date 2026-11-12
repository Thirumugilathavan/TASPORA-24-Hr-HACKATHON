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


class FacilityServiceResponse(BaseModel):
    id: UUID
    service_name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None

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
    state: Optional[str] = None
    subdistrict: Optional[str] = None
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in range [-90.0, 90.0]")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in range [-180.0, 180.0]")
    ownership: Optional[str] = "Government"
    source: Optional[str] = "nic"
    source_id: Optional[str] = None
    contact_details: Optional[Dict[str, Any]] = None

    @field_validator("facility_type")
    @classmethod
    def validate_facility_type(cls, v: str) -> str:
        v_upper = v.strip().upper()
        allowed = {t.value for t in FacilityType}
        if v_upper not in allowed:
            raise ValueError(f"Invalid facility_type '{v}'. Allowed types: {sorted(allowed)}")
        return v_upper

    @field_validator("name", "address")
    @classmethod
    def strip_and_validate_non_empty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Field cannot be empty or whitespace only")
        return s


class FacilityCreate(FacilityBase):
    village_id: UUID = Field(..., description="Village UUID for facility creation")
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
    doctors: List[DoctorSummary] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
