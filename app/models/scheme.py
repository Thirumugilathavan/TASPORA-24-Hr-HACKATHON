"""
SQLAlchemy models for NALAM Scheme Finder — Government Schemes & Financial Benefits.
Includes Government Schemes Registry, User Consented Scheme Profiles, Saved Schemes, and Audit Logs.
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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class GovernmentScheme(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Registry of verified Central and Tamil Nadu Government welfare, subsidy,
    healthcare, scholarship, and financial assistance schemes.
    """
    __tablename__ = "government_schemes"

    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name_ta: Mapped[str] = mapped_column(String(300), nullable=False)
    short_description: Mapped[str] = mapped_column(Text, nullable=False)
    short_description_ta: Mapped[str] = mapped_column(Text, nullable=False)
    detailed_description: Mapped[str] = mapped_column(Text, nullable=False)
    detailed_description_ta: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Department & Administration
    department: Mapped[str] = mapped_column(String(255), nullable=False)
    department_ta: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[str] = mapped_column(String(50), default="STATE", nullable=False, index=True)  # CENTRAL, STATE, DISTRICT, LOCAL
    state: Mapped[str] = mapped_column(String(100), default="Tamil Nadu", nullable=False, index=True)
    districts: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)  # ["ALL"] or specific districts
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # HEALTHCARE, AGRICULTURE, EDUCATION, WOMEN_CHILD, PENSION, HOUSING, FINANCIAL_AID, DISABILITY, EMPLOYMENT
    
    # Target Beneficiaries & Benefits
    target_beneficiaries: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    target_beneficiaries_ta: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    benefit_type: Mapped[str] = mapped_column(String(100), nullable=False)  # CASH_TRANSFER, HEALTH_INSURANCE, SUBSIDY, SCHOLARSHIP, PENSION, LOAN_CONCESSION, HOUSING_GRANT
    benefit_amount_desc: Mapped[str] = mapped_column(String(255), nullable=False)
    benefit_amount_desc_ta: Mapped[str] = mapped_column(String(255), nullable=False)
    benefit_frequency: Mapped[str] = mapped_column(String(100), default="ONE_TIME", nullable=False)  # ANNUAL, MONTHLY, ONE_TIME, PER_EPISODE
    
    # Structured Eligibility Rules for Deterministic Engine
    eligibility_rules: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    
    # Documentation & Application Process
    required_documents: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    application_mode: Mapped[str] = mapped_column(String(100), default="ONLINE", nullable=False)  # ONLINE, E_SEVAI, DISTRICT_OFFICE, PHC_HOSPITAL, BOTH
    application_process: Mapped[str] = mapped_column(Text, nullable=False)
    application_process_ta: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Official Source & Portal Verification
    official_portal_url: Mapped[str] = mapped_column(String(500), nullable=False)
    official_source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    application_status: Mapped[str] = mapped_column(String(50), default="ALWAYS_OPEN", nullable=False)  # ALWAYS_OPEN, OPEN, CLOSED, UPCOMING
    last_verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    verification_status: Mapped[str] = mapped_column(String(50), default="OFFICIALLY_VERIFIED", nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    saved_by_users: Mapped[List["SavedUserScheme"]] = relationship(
        "SavedUserScheme",
        back_populates="scheme",
        cascade="all, delete-orphan",
    )


class UserSchemeProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Consented multi-step questionnaire responses for personalized scheme eligibility.
    Strictly isolated per user; optional fields are respectful of privacy.
    """
    __tablename__ = "user_scheme_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    step_progress: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Profile sections stored as structured JSON
    profile_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    user: Mapped["User"] = relationship("User", backref="scheme_profile")


class SavedUserScheme(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    User-bookmarked government schemes for easy access and document checklist tracking.
    """
    __tablename__ = "saved_user_schemes"
    __table_args__ = (
        UniqueConstraint("user_id", "scheme_id", name="uq_user_saved_scheme"),
        Index("ix_saved_schemes_user_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    scheme_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("government_schemes.id", ondelete="CASCADE"),
        nullable=False,
    )
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    scheme: Mapped["GovernmentScheme"] = relationship("GovernmentScheme", back_populates="saved_by_users")


class SchemeAuditLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Administrative audit trail for verified scheme alterations and status changes.
    """
    __tablename__ = "scheme_audit_logs"

    scheme_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("government_schemes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # CREATE, UPDATE, VERIFY, DEACTIVATE
    changes_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
