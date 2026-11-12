import uuid
from typing import Optional
from sqlalchemy import Enum, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.shared import RequestType, Urgency


class HealthcareRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Healthcare request model initiated by patients or ASHA workers."""
    __tablename__ = "healthcare_requests"

    patient_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    request_type: Mapped[RequestType] = mapped_column(
        Enum(RequestType, name="request_type_enum", native_enum=False),
        nullable=False,
        index=True
    )
    medicine_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    urgency: Mapped[Urgency] = mapped_column(
        Enum(Urgency, name="urgency_enum", native_enum=False),
        nullable=False,
        default=Urgency.NORMAL
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING", index=True)
