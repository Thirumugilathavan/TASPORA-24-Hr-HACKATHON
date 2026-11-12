from datetime import date, datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.schemas.shared import AttendanceStatus


class DoctorBase(BaseModel):
    name: str
    facility_id: UUID
    specialization: str
    qualification: Optional[str] = None
    contact_phone: Optional[str] = None


class DoctorCreate(DoctorBase):
    pass


class DoctorResponse(DoctorBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DoctorScheduleBase(BaseModel):
    schedule_date: date
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    attendance_status: AttendanceStatus = AttendanceStatus.EXPECTED
    notes: Optional[str] = None


class DoctorScheduleCreate(DoctorScheduleBase):
    doctor_id: UUID
    facility_id: UUID


class DoctorScheduleResponse(DoctorScheduleBase):
    id: UUID
    doctor_id: UUID
    facility_id: UUID
    last_verified_at: Optional[datetime] = None
    verified_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DoctorScheduleDetailResponse(BaseModel):
    doctor_id: UUID
    doctor_name: str
    facility_id: UUID
    date: date
    attendance_status: AttendanceStatus
    last_verified_at: Optional[datetime] = None
    schedule: Optional[DoctorScheduleResponse] = None

    model_config = ConfigDict(from_attributes=True)
