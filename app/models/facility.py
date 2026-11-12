import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import Float, ForeignKey, Index, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Facility(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Healthcare facility entity (PHC, CHC, Hospital, Sub-Centre, Pharmacy)."""
    __tablename__ = "facilities"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    facility_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    village_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True, index=True)
    district: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default="", index=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default="", index=True)
    subdistrict: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default="")
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    ownership: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default="Government")
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="nic")
    source_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    contact_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_facilities_coords", "latitude", "longitude"),
    )

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
