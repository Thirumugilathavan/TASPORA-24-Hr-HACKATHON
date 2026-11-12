from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class IVRSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tracks telephony IVR call sessions and interactive state transitions."""
    __tablename__ = "ivr_sessions"

    call_sid: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    caller_phone: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    patient_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("patients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    language: Mapped[str] = mapped_column(String(10), default="ta", nullable=False)
    current_menu: Mapped[str] = mapped_column(String(50), default="LANGUAGE_SELECT", nullable=False, index=True)
    menu_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="IN_PROGRESS", nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_interaction_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    interactions: Mapped[List["IVRInteraction"]] = relationship(
        "IVRInteraction",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="IVRInteraction.created_at.asc()",
    )


class IVRInteraction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Detailed audit trail of DTMF inputs, prompts played, and actions taken."""
    __tablename__ = "ivr_interactions"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ivr_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    menu_name: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_played: Mapped[str] = mapped_column(Text, nullable=False)
    dtmf_input: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    action_taken: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    session: Mapped["IVRSession"] = relationship("IVRSession", back_populates="interactions")


class IVRAuthAttempt(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Rate-limiting and anti-brute-force tracker for IVR PIN verification."""
    __tablename__ = "ivr_auth_attempts"

    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    attempts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
