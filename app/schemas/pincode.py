from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class PincodeResolutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pincode: str = Field(..., description="6-digit Indian Postal PIN code")
    locality: str = Field(..., description="Resolved post office or postal sub-region name")
    district: str = Field(..., description="District name")
    state: str = Field(..., description="State or Union Territory name")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Approximate centroid latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Approximate centroid longitude")
    is_approximate: bool = Field(True, description="Flag indicating coordinates represent postal area, not exact GPS")
    confidence: str = Field(..., description="'EXACT' for known post office, 'POSTAL_CIRCLE' for regional prefix")
    message: str = Field(..., description="Human-readable resolution status message")
