from typing import Optional
from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Village(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Rural village entity for location reference and distance calculation."""
    __tablename__ = "villages"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
