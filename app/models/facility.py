import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, JSON, String, Uuid
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
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default="Tamil Nadu", index=True)
    subdistrict: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default="")
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    ownership: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default="Government", index=True)
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="nic")
    source_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    contact_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Extended verified healthcare fields
    alternate_names: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    facility_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default="HOSPITAL", index=True)
    health_unit_district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    block: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    locality: Mapped[Optional[str]] = mapped_column(String(150), nullable=True, index=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    geographic_verification_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="VERIFIED_COORDINATES")
    official_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    official_email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    official_website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    emergency_contact: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    opd_available: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=True)
    opening_hours: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    emergency_services: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=False, index=True)
    ambulance_available: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=False)
    maternity_services: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=False, index=True)
    pharmacy_available: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=True)
    laboratory_services: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=True)
    imaging_services: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=False)
    specialties: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    appointment_booking_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="WALK_IN_ONLY", index=True)
    online_booking_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    official_source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    date_collected: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_verified_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    verification_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="VERIFIED_OFFICIAL", index=True)
    data_completeness_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0.0)

    __table_args__ = (
        Index("ix_facilities_coords", "latitude", "longitude"),
        Index("ix_facilities_district_block", "district", "block"),
        Index("ix_facilities_services", "emergency_services", "maternity_services"),
    )

    # Relationships
    services: Mapped[List["FacilityService"]] = relationship(
        "FacilityService",
        back_populates="facility",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    specialties_rel: Mapped[List["FacilitySpecialty"]] = relationship(
        "FacilitySpecialty",
        back_populates="facility",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    sources_rel: Mapped[List["FacilitySource"]] = relationship(
        "FacilitySource",
        back_populates="facility",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    verification_history: Mapped[List["FacilityVerificationHistory"]] = relationship(
        "FacilityVerificationHistory",
        back_populates="facility",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    appointment_config: Mapped[Optional["FacilityAppointmentConfig"]] = relationship(
        "FacilityAppointmentConfig",
        back_populates="facility",
        cascade="all, delete-orphan",
        uselist=False,
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


class FacilitySpecialty(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Normalized medical specialty verified at a facility."""
    __tablename__ = "facility_specialties"

    facility_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("facilities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    specialty_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    facility: Mapped["Facility"] = relationship("Facility", back_populates="specialties_rel")


class FacilitySource(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Source provenance and audit trail for facility data."""
    __tablename__ = "facility_sources"

    facility_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("facilities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    date_collected: Mapped[str] = mapped_column(String(50), nullable=False)
    verification_notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    facility: Mapped["Facility"] = relationship("Facility", back_populates="sources_rel")


class FacilityVerificationHistory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Verification audit log."""
    __tablename__ = "facility_verification_history"

    facility_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("facilities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    verification_status: Mapped[str] = mapped_column(String(50), nullable=False)
    verified_by: Mapped[str] = mapped_column(String(100), nullable=False)
    verification_date: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    facility: Mapped["Facility"] = relationship("Facility", back_populates="verification_history")


class FacilityAppointmentConfig(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Verified appointment and OPD booking configuration."""
    __tablename__ = "facility_appointment_configurations"

    facility_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("facilities.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    booking_method: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    booking_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    booking_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    instructions_en: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    instructions_ta: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    requires_registration: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    facility: Mapped["Facility"] = relationship("Facility", back_populates="appointment_config")
