from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


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
    name: str
    facility_type: str
    address: str
    village_id: UUID
    latitude: float
    longitude: float
    contact_details: Optional[Dict[str, Any]] = None


class FacilityCreate(FacilityBase):
    services: Optional[List[str]] = []


class FacilityResponse(FacilityBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FacilityDetailResponse(FacilityBase):
    id: UUID
    services: List[FacilityServiceResponse] = []
    doctors: List[DoctorSummary] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
