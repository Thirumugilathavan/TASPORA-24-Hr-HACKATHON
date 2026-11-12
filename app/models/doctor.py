from datetime import date, datetime
from typing import List, Optional, TYPE_CHECKING
import uuid
from sqlalchemy import Date, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.facility import Facility
    from app.models.user import User


class Doctor(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Healthcare practitioner assigned to a facility."""
    __tablename__ = "doctors"

    facility_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("facilities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        unique=True,
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    specialization: Mapped[str] = mapped_column(String(150), nullable=False)
    qualification: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    facility: Mapped["Facility"] = relationship("Facility", back_populates="doctors")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="doctor")
    schedules: Mapped[List["DoctorSchedule"]] = relationship(
        "DoctorSchedule",
        back_populates="doctor",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class DoctorSchedule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Doctor schedule duty and attendance log.

    IMPORTANT: EXPECTED denotes planned shift schedule, not confirmed attendance.
    PRESENT / ABSENT denotes confirmed attendance verification.
    """
    __tablename__ = "doctor_schedules"

    doctor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("doctors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("facilities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    schedule_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    end_time: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    attendance_status: Mapped[str] = mapped_column(
        String(20),
        default="EXPECTED",
        nullable=False,
        index=True,
    )
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    verified_by: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="schedules")
