from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.shared import Role


class RegisterIn(BaseModel):
    """Registration request schema.

    Public registration creates PATIENT role accounts only.
    Client-supplied role parameters are overridden by the server.
    Phone numbers can include country prefixes (e.g. +91) and formatting,
    which will be normalized to canonical 10-digit format by the server.
    """
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=25, description="Indian mobile number, optionally prefixed with +91 or formatted with spaces.")
    password: str = Field(..., min_length=6, max_length=128)
    role: Optional[Role] = Field(default=Role.PATIENT, description="Public registrations are constrained to PATIENT role.")


class LoginIn(BaseModel):
    """Login request schema.

    Authenticates using registered phone number (normalized automatically) and password.
    """
    phone: str = Field(..., min_length=10, max_length=25, description="Indian mobile number, optionally prefixed with +91 or formatted with spaces.")
    password: str = Field(..., min_length=1, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: UUID


class UserOut(BaseModel):
    id: UUID
    name: str
    phone: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
