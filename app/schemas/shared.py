"""Shared Pydantic schemas for the CareBridge API contract v1.
Put in app/schemas/. Each module owner imports from here; do not rename fields."""
from datetime import date, datetime, time
from enum import Enum
from typing import Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

T = TypeVar("T")


# ---------- enums ----------
class Role(str, Enum):
    PATIENT = "PATIENT"; ASHA = "ASHA"; DOCTOR = "DOCTOR"; STAFF = "STAFF"; ADMIN = "ADMIN"

class AvailabilityStatus(str, Enum):
    IN_STOCK = "IN_STOCK"; LOW = "LOW"; OUT = "OUT"; UNKNOWN = "UNKNOWN"

class SourceType(str, Enum):
    STAFF = "STAFF"; ASHA = "ASHA"; PATIENT = "PATIENT"

class AvailabilityLabel(str, Enum):
    LIKELY = "LIKELY"; UNCERTAIN = "UNCERTAIN"; UNLIKELY = "UNLIKELY"

class RequestType(str, Enum):
    CONSULTATION = "CONSULTATION"
    REFILL = "REFILL"
    CHECKUP = "CHECKUP"
    DIAGNOSTIC = "DIAGNOSTIC"
    CAMP_FOLLOWUP = "CAMP_FOLLOWUP"
    SCHEME_ASSISTANCE = "SCHEME_ASSISTANCE"
    FACILITY_ASSISTANCE = "FACILITY_ASSISTANCE"

class Urgency(str, Enum):
    NORMAL = "NORMAL"; PRIORITY = "PRIORITY"; URGENT = "URGENT"

class AttendanceStatus(str, Enum):
    EXPECTED = "EXPECTED"; PRESENT = "PRESENT"; ABSENT = "ABSENT"; UNKNOWN = "UNKNOWN"

class AppointmentStatus(str, Enum):
    BOOKED = "BOOKED"; CONFIRMED = "CONFIRMED"; CANCELLED = "CANCELLED"; COMPLETED = "COMPLETED"


# ---------- common ----------
class ErrorBody(BaseModel):
    code: str
    message: str

class ErrorResponse(BaseModel):
    error: ErrorBody

class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int


# ---------- stock (Person 3) ----------
class StockReportIn(BaseModel):          # source_type is set by the server, not sent
    facility_id: UUID
    medicine_id: UUID
    availability_status: AvailabilityStatus

class BeliefSnapshot(BaseModel):
    p_available: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)

class StockReportOut(BaseModel):
    report_id: UUID
    verification_status: str = "PENDING"
    updated: BeliefSnapshot

class AvailabilityItem(BaseModel):
    facility_id: UUID
    p_available: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    label: AvailabilityLabel
    evidence_count: int
    last_report_at: Optional[datetime] = None

class AvailabilityOut(BaseModel):
    medicine_id: UUID
    items: List[AvailabilityItem]


# ---------- requests and recommendations (Person 4) ----------
class RequestIn(BaseModel):
    patient_id: UUID
    request_type: RequestType
    title: Optional[str] = None
    medicine_id: Optional[UUID] = None
    facility_id: Optional[UUID] = None
    camp_id: Optional[UUID] = None
    preferred_date: Optional[date] = None
    contact_phone: Optional[str] = None
    extra_metadata: Optional[str] = None
    description: str = ""
    urgency: Urgency = Urgency.NORMAL

class RequestOut(BaseModel):
    id: UUID
    status: str = "PENDING"
    created_at: datetime
    patient_id: Optional[UUID] = None
    request_type: Optional[RequestType] = None
    title: Optional[str] = None
    medicine_id: Optional[UUID] = None
    facility_id: Optional[UUID] = None
    camp_id: Optional[UUID] = None
    preferred_date: Optional[date] = None
    contact_phone: Optional[str] = None
    extra_metadata: Optional[str] = None
    description: Optional[str] = None
    urgency: Optional[Urgency] = None

class RecommendationItem(BaseModel):
    rank: int
    facility_id: UUID
    facility_name: str
    suitability_score: float = Field(ge=0, le=1)
    medicine_confidence: float = Field(ge=0, le=1)
    travel_distance_km: int
    travel_cost: int
    failure_probability: float = Field(ge=0, le=1)
    expected_loss: int                    # = failure_probability * travel_cost
    doctor_status: AttendanceStatus
    explanation: str

class RecommendationOut(BaseModel):
    request_id: UUID
    items: List[RecommendationItem]       # sorted ascending by expected_loss


# ---------- appointments (Person 4) ----------
class AppointmentIn(BaseModel):
    patient_id: UUID
    facility_id: UUID
    doctor_id: Optional[UUID] = None
    request_id: Optional[UUID] = None
    appointment_date: date
    appointment_time: time

class AppointmentOut(BaseModel):
    id: UUID
    status: AppointmentStatus = AppointmentStatus.BOOKED


# ---------- IVR channel ----------
class IVRLookupIn(BaseModel):
    phone: str
    medicine_code: str                    # e.g. "bp", "diabetes", "iron", "ors"

class IVRLookupOut(BaseModel):
    speak_text: str                       # ready to read aloud; no dosage or diagnosis
    facility_id: UUID
    p_available: float = Field(ge=0, le=1)
    options: List[RecommendationItem]

class IVRFeedbackIn(BaseModel):
    phone: str
    facility_id: UUID
    medicine_code: str
    got_it: bool
