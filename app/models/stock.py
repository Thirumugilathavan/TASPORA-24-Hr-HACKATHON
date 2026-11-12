from datetime import datetime, timezone
from typing import Optional
import uuid
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StockReport(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Append-only ledger of medicine inventory reports from staff, ASHA, and patients."""
    __tablename__ = "stock_reports"

    facility_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("facilities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    medicine_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("medicines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    availability_status: Mapped[str] = mapped_column(String(20), nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(20),
        default="PENDING",
        nullable=False,
    )
    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    facility: Mapped["Facility"] = relationship("Facility", back_populates="stock_reports")
    medicine: Mapped["Medicine"] = relationship("Medicine", back_populates="stock_reports")


class FacilityMedicineBelief(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Derived probabilistic belief state for medicine availability at a facility."""
    __tablename__ = "facility_medicine_beliefs"
    __table_args__ = (
        UniqueConstraint("facility_id", "medicine_id", name="uq_facility_medicine_belief"),
    )

    facility_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("facilities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    medicine_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("medicines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    p_available: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    label: Mapped[str] = mapped_column(String(20), default="UNCERTAIN", nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_report_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    facility: Mapped["Facility"] = relationship("Facility", back_populates="belief_states")
    medicine: Mapped["Medicine"] = relationship("Medicine", back_populates="belief_states")
