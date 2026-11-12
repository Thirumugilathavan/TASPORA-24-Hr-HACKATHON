from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.shared import Role


class RegisterIn(BaseModel):
    """Registration request schema.
    Public registration creates PATIENT role accounts only.
    Client-supplied role parameters are overridden by the server.
    """
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=6, max_length=128)
    role: Optional[Role] = Field(default=Role.PATIENT, description="Public registrations are constrained to PATIENT role.")


class LoginIn(BaseModel):
    phone: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=1)


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
