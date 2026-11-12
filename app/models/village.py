from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.patient import Patient


class Village(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Village registry model with GPS coordinates for healthcare routing and facility matching."""
    __tablename__ = "villages"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    district: Mapped[str] = mapped_column(String(255), nullable=False, default="", index=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Restrict cascade: deleting a village record must NEVER cascade-delete patient records
    patients: Mapped[List["Patient"]] = relationship(
        "Patient",
        back_populates="village",
    )

    @validates("latitude")
    def validate_latitude(self, key, value):
        val = float(value)
        if not (-90.0 <= val <= 90.0):
            raise ValueError(f"Latitude must be between -90.0 and 90.0, got {val}")
        return val

    @validates("longitude")
    def validate_longitude(self, key, value):
        val = float(value)
        if not (-180.0 <= val <= 180.0):
            raise ValueError(f"Longitude must be between -180.0 and 180.0, got {val}")
        return val

    @validates("name", "district")
    def validate_strings(self, key, value):
        if not value or not str(value).strip():
            raise ValueError(f"{key} cannot be empty")
        return str(value).strip()
