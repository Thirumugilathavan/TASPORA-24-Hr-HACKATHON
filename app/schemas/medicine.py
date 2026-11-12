from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class MedicineBase(BaseModel):
    name: str
    generic_name: Optional[str] = None
    strength: Optional[str] = None
    dosage_form: Optional[str] = None


class MedicineCreate(MedicineBase):
    pass


class MedicineResponse(MedicineBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
