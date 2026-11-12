from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class MedicineBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Brand or catalogue name of the medicine")
    generic_name: Optional[str] = Field(None, max_length=255, description="Generic pharmacological compound name")
    strength: Optional[str] = Field(None, max_length=100, description="Catalogue strength (e.g., 500mg)")
    dosage_form: Optional[str] = Field(None, max_length=100, description="Catalogue form (e.g., Tablet, Syrup)")

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Medicine name cannot be empty or whitespace only")
        return s

    @field_validator("generic_name", "strength", "dosage_form")
    @classmethod
    def strip_optional_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            s = v.strip()
            return s if s else None
        return None


class MedicineCreate(MedicineBase):
    pass


class MedicineResponse(MedicineBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
