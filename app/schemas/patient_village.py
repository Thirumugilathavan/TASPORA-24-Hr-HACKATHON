import re
from datetime import date, datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.shared import Page

PHONE_REGEX = re.compile(r"^[6-9]\d{9}$")

SUPPORTED_LANGUAGES = {
    "ta": "Tamil",
    "tamil": "Tamil",
    "en": "English",
    "english": "English",
    "hi": "Hindi",
    "hindi": "Hindi",
    "te": "Telugu",
    "telugu": "Telugu",
    "bn": "Bengali",
    "bengali": "Bengali",
    "kn": "Kannada",
    "kannada": "Kannada",
    "ml": "Malayalam",
    "malayalam": "Malayalam",
    "mr": "Marathi",
    "marathi": "Marathi",
}


class VillageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    district: str
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    is_synthetic: bool = True


class VillageIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    district: str = Field(..., min_length=1, max_length=255)
    state: Optional[str] = Field(default=None, max_length=100)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    is_synthetic: bool = True

    @field_validator("name", "district")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty or whitespace only")
        return cleaned


class VillageListOut(Page[VillageOut]):
    pass


class PatientIn(BaseModel):
    village_id: UUID
    date_of_birth: date
    preferred_language: str = Field(default="ta", min_length=2, max_length=50)
    consent_given: Optional[bool] = Field(default=False)
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
        # Validate that language code or name is recognized
        if cleaned not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language: '{v}'. Supported languages include: "
                "Tamil ('ta'), English ('en'), Hindi ('hi'), Telugu ('te'), Bengali ('bn')."
            )
        return cleaned

    @field_validator("emergency_contact_phone")
    @classmethod
    def validate_emergency_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = re.sub(r"[\s\-\+]", "", str(v).strip())
        if not cleaned:
            return None
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
    consent_given: bool = False
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
    consent_given: bool = False
    emergency_contact_phone: Optional[str] = None
    created_at: Optional[datetime] = None
