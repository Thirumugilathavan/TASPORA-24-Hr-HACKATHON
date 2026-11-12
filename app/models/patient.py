import uuid
from datetime import date
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Boolean, Date, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.village import Village


class Patient(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Patient demographic profile linked 1-to-1 with a User account and a Village."""
    __tablename__ = "patients"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
        index=True,
    )
    village_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("villages.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(50), nullable=False, default="hi")
    consent_given: Mapped[Optional[bool]] = mapped_column(Boolean, default=True, nullable=True)
    emergency_contact_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="patient")
    village: Mapped["Village"] = relationship("Village", back_populates="patients")
