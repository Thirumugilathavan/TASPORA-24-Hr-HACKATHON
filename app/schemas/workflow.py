from datetime import date, datetime, time
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.shared import AppointmentStatus, RequestType, Urgency


class RequestDetailOut(BaseModel):
    """Detailed response schema for a healthcare request."""
    id: UUID
    patient_id: UUID
    request_type: RequestType
    medicine_id: Optional[UUID] = None
    description: str
    urgency: Urgency
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecommendationCreateIn(BaseModel):
    """Payload to trigger recommendation generation."""
    request_id: UUID


class AppointmentDetailOut(BaseModel):
    """Detailed response schema for an appointment booking."""
    id: UUID
    patient_id: UUID
    facility_id: UUID
    doctor_id: Optional[UUID] = None
    request_id: Optional[UUID] = None
    appointment_date: date
    appointment_time: time
    status: AppointmentStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AppointmentCancelOut(BaseModel):
    """Response schema following appointment cancellation."""
    id: UUID
    status: AppointmentStatus

    model_config = ConfigDict(from_attributes=True)
