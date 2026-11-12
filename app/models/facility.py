import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import Float, ForeignKey, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Facility(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Healthcare facility entity (PHC, CHC, Hospital, Pharmacy)."""
    __tablename__ = "facilities"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    facility_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    village_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    contact_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    services: Mapped[List["FacilityService"]] = relationship(
        "FacilityService",
        back_populates="facility",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    doctors: Mapped[List["Doctor"]] = relationship(
        "Doctor",
        back_populates="facility",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    stock_reports: Mapped[List["StockReport"]] = relationship(
        "StockReport",
        back_populates="facility",
        cascade="all, delete-orphan",
    )
    belief_states: Mapped[List["FacilityMedicineBelief"]] = relationship(
        "FacilityMedicineBelief",
        back_populates="facility",
        cascade="all, delete-orphan",
    )


class FacilityService(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Specific healthcare service offered at a facility."""
    __tablename__ = "facility_services"

    facility_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("facilities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    facility: Mapped["Facility"] = relationship("Facility", back_populates="services")
