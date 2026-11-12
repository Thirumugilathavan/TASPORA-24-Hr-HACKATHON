from typing import List, TYPE_CHECKING
from sqlalchemy import Boolean, Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.patient import Patient


class Village(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Village registry model with GPS coordinates for healthcare routing and facility matching."""
    __tablename__ = "villages"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    district: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    patients: Mapped[List["Patient"]] = relationship(
        "Patient",
        back_populates="village",
        cascade="all, delete-orphan",
    )
