import uuid
from datetime import date, time
from typing import Optional
from sqlalchemy import Date, Enum, ForeignKey, Index, Time, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.shared import AppointmentStatus


class Appointment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Appointment booking model with concurrency conflict protection."""
    __tablename__ = "appointments"

    patient_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    facility_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    doctor_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True, index=True)
    request_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("healthcare_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    appointment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    appointment_time: Mapped[time] = mapped_column(Time, nullable=False, index=True)
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus, name="appointment_status_enum", native_enum=False),
        nullable=False,
        default=AppointmentStatus.BOOKED,
        index=True
    )

    __table_args__ = (
        # Conflict Prevention 1: Active booking for specific doctor on date & time
        Index(
            "uq_active_doctor_slot",
            "doctor_id",
            "appointment_date",
            "appointment_time",
            unique=True,
            postgresql_where=text("doctor_id IS NOT NULL AND status != 'CANCELLED'"),
            sqlite_where=text("doctor_id IS NOT NULL AND status != 'CANCELLED'"),
        ),
        # Conflict Prevention 2: Active booking for unassigned facility walk-in slot on date & time
        Index(
            "uq_active_facility_unassigned_slot",
            "facility_id",
            "appointment_date",
            "appointment_time",
            unique=True,
            postgresql_where=text("doctor_id IS NULL AND status != 'CANCELLED'"),
            sqlite_where=text("doctor_id IS NULL AND status != 'CANCELLED'"),
        ),
    )
