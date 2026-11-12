"""
Pydantic schemas for Health Camps, Official Sources, Coverage Registry, and User Preferences.
"""

from datetime import datetime
import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class HealthCampSourceOut(BaseModel):
    id: uuid.UUID
    name: str
    organization: str
    source_url: str
    collector_type: str
    district: Optional[str] = None
    is_active: bool
    check_interval_hours: int
    last_checked_at: Optional[datetime] = None
    last_status: str
    last_error: Optional[str] = None
    events_discovered_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HealthCampSourceCreateIn(BaseModel):
    name: str = Field(..., min_length=3, max_length=200)
    organization: str = Field(..., min_length=3, max_length=250)
    source_url: str = Field(..., min_length=10, max_length=500)
    collector_type: str = Field("NHM_WP_API", description="NHM_WP_API, NHM_MMU_REGISTRY, DISTRICT_NIC_PORTAL, OFFICIAL_CIRCULAR")
    district: Optional[str] = None
    check_interval_hours: int = Field(6, ge=1, le=168)
    is_active: bool = True


class HealthCampOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    category: str
    organizing_dept: str
    start_date: datetime
    end_date: Optional[datetime] = None
    venue_name: str
    full_address: str
    village: Optional[str] = None
    town: Optional[str] = None
    taluk: Optional[str] = None
    district: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    services_offered: List[str] = []
    eligibility: Optional[str] = None
    registration_instructions: Optional[str] = None
    contact_info: Optional[str] = None
    source_id: Optional[uuid.UUID] = None
    source_org: str
    source_url: str
    publication_date: Optional[datetime] = None
    discovered_at: datetime
    last_checked_at: datetime
    verification_status: str
    event_status: str
    followup_instructions: Optional[str] = None
    followup_facility_id: Optional[uuid.UUID] = None
    provenance: Dict[str, Any] = {}
    distance_km: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HealthCampListResponse(BaseModel):
    items: List[HealthCampOut]
    total: int
    user_location: Optional[Dict[str, Any]] = None
    filters_applied: Dict[str, Any] = {}


class DistrictCoverageItem(BaseModel):
    district: str
    district_ta: str
    headquarters: str
    portal_url: str
    verified_events_count: int
    last_checked_at: Optional[datetime] = None
    check_status: str  # SUCCESS, PENDING, ERROR
    coverage_status: str  # VERIFIED_EVENTS_AVAILABLE, NO_PUBLISHED_EVENTS, INSUFFICIENT_DATA


class DistrictCoverageResponse(BaseModel):
    districts: List[DistrictCoverageItem]
    total_districts: int
    total_verified_camps: int
    districts_with_events_count: int
    monitored_sources_count: int
    last_collection_timestamp: Optional[datetime] = None


class CampVerificationUpdateIn(BaseModel):
    verification_status: str = Field(..., pattern="^(VERIFIED|UNVERIFIED|FLAGGED|REJECTED)$")
    event_status: Optional[str] = Field(None, pattern="^(UPCOMING|ONGOING|COMPLETED|CANCELLED|POSTPONED|DATE_UNCONFIRMED)$")
    followup_instructions: Optional[str] = None
    notes: Optional[str] = None


class UserCampPreferenceIn(BaseModel):
    opt_in: bool = True
    preferred_districts: List[str] = []
    max_distance_km: int = Field(30, ge=5, le=200)
    notify_categories: List[str] = []


class UserCampPreferenceOut(BaseModel):
    user_id: uuid.UUID
    opt_in: bool
    preferred_districts: List[str]
    max_distance_km: int
    notify_categories: List[str]

    class Config:
        from_attributes = True
