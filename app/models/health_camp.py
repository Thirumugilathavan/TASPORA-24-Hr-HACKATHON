"""
SQLAlchemy models for Statewide Tamil Nadu Health Camps, Outreach Events,
Configurable Official Sources, and User Notification Preferences.
"""

from datetime import datetime, timezone
import uuid
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    String,
    Text,
    Float,
    Boolean,
    Integer,
    DateTime,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class HealthCampSource(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Configurable official government health camp and outreach event source registry.
    """
    __tablename__ = "health_camp_sources"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    organization: Mapped[str] = mapped_column(String(250), nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    collector_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="NHM_WP_API"
    )  # NHM_WP_API, NHM_MMU_REGISTRY, DISTRICT_NIC_PORTAL, OFFICIAL_CIRCULAR
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    check_interval_hours: Mapped[int] = mapped_column(Integer, default=6, nullable=False)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    events_discovered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    config_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    camps: Mapped[List["HealthCamp"]] = relationship(
        "HealthCamp", back_populates="source", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_camp_sources_active", "is_active", "district"),
    )


class HealthCamp(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Statewide Health Camp, Outreach Session, or Mobile Medical Unit Event.
    """
    __tablename__ = "health_camps"

    title: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        String(60), nullable=False, default="GENERAL_HEALTH_CAMP", index=True
    )  # GENERAL_HEALTH_CAMP, MOBILE_MEDICAL_UNIT, NCD_SCREENING, EYE_CAMP, MATERNAL_CHILD_HEALTH, VACCINATION_DRIVE, SPECIALIST_OUTREACH
    organizing_dept: Mapped[str] = mapped_column(String(250), nullable=False)
    
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    venue_name: Mapped[str] = mapped_column(String(250), nullable=False)
    full_address: Mapped[str] = mapped_column(Text, nullable=False)
    village: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    town: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    taluk: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    district: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    services_offered: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    eligibility: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    registration_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("health_camp_sources.id", ondelete="SET NULL"), nullable=True
    )
    source_org: Mapped[str] = mapped_column(String(250), nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    publication_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    
    verification_status: Mapped[str] = mapped_column(
        String(50), default="VERIFIED", nullable=False, index=True
    )  # VERIFIED, UNVERIFIED, FLAGGED, REJECTED
    event_status: Mapped[str] = mapped_column(
        String(50), default="UPCOMING", nullable=False, index=True
    )  # UPCOMING, ONGOING, COMPLETED, CANCELLED, POSTPONED, DATE_UNCONFIRMED
    
    followup_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    followup_facility_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("facilities.id", ondelete="SET NULL"), nullable=True
    )
    
    provenance: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    dedup_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    source: Mapped[Optional["HealthCampSource"]] = relationship("HealthCampSource", back_populates="camps")
    followup_facility: Mapped[Optional["Facility"]] = relationship("Facility")

    __table_args__ = (
        Index("ix_health_camps_district_status", "district", "event_status"),
        Index("ix_health_camps_start_date_status", "start_date", "event_status"),
    )


class UserCampPreference(Base, TimestampMixin):
    """
    User notification preferences for health camp discovery.
    """
    __tablename__ = "user_camp_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    opt_in: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    preferred_districts: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    max_distance_km: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    notify_categories: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
