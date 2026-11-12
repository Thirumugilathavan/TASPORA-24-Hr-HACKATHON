import re
from datetime import date, datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.shared import Page

PHONE_REGEX = re.compile(r"^[6-9]\d{9}$")


class VillageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    district: str
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class VillageListOut(Page[VillageOut]):
    pass


class PatientIn(BaseModel):
    village_id: UUID
    date_of_birth: date
    preferred_language: str = Field(..., min_length=2, max_length=50)
    consent_given: Optional[bool] = Field(default=True)
    emergency_contact_phone: Optional[str] = Field(default=None)

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Date of birth cannot be in the future")
        if v.year < 1900:
            raise ValueError("Invalid date of birth: year must be 1900 or later")
        return v

    @field_validator("preferred_language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if not cleaned:
            raise ValueError("Preferred language cannot be empty")
        return cleaned

    @field_validator("emergency_contact_phone")
    @classmethod
    def validate_emergency_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        cleaned = re.sub(r"[\s\-\+]", "", v)
        if cleaned.startswith("91") and len(cleaned) == 12:
            cleaned = cleaned[2:]
        if not PHONE_REGEX.match(cleaned):
            raise ValueError("Emergency contact must be a valid 10-digit mobile number")
        return cleaned


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    village_id: UUID
    date_of_birth: date
    preferred_language: str
    consent_given: Optional[bool] = True
    created_at: Optional[datetime] = None


class PatientDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: Optional[str] = None
    phone: Optional[str] = None
    village: VillageOut
    date_of_birth: date
    preferred_language: str
    consent_given: Optional[bool] = True
    emergency_contact_phone: Optional[str] = None
    created_at: Optional[datetime] = None
