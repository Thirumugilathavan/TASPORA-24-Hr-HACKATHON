import uuid
from datetime import date
from typing import Optional
from sqlalchemy import Date, Enum, Index, String, Text, Uuid
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
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    medicine_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True, index=True)
    facility_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True, index=True)
    camp_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True, index=True)
    preferred_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    extra_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    urgency: Mapped[Urgency] = mapped_column(
        Enum(Urgency, name="urgency_enum", native_enum=False),
        nullable=False,
        default=Urgency.NORMAL
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING", index=True)
