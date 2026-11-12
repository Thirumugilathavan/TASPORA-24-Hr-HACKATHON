from datetime import date, datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.schemas.shared import AttendanceStatus


class DoctorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    facility_id: UUID
    specialization: str = Field(..., min_length=1, max_length=150)
    qualification: Optional[str] = Field(None, max_length=150)
    contact_phone: Optional[str] = Field(None, max_length=50)

    @field_validator("name", "specialization")
    @classmethod
    def strip_and_validate(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Field cannot be empty or whitespace only")
        return s


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

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.start_time and self.end_time:
            st = self.start_time.strip()
            et = self.end_time.strip()
            if st >= et:
                raise ValueError(f"Schedule start_time '{st}' must be strictly before end_time '{et}'")
        return self


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
