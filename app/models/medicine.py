from typing import List, Optional
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Medicine(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Medicine catalogue item.

    DISCLOSURE: Catalogue metadata only.
    Medical diagnosis, prescription generation, and dosage recommendations are strictly out of scope.
    """
    __tablename__ = "medicines"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    generic_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    strength: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    dosage_form: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    stock_reports: Mapped[List["StockReport"]] = relationship(
        "StockReport",
        back_populates="medicine",
        cascade="all, delete-orphan",
    )
    belief_states: Mapped[List["FacilityMedicineBelief"]] = relationship(
        "FacilityMedicineBelief",
        back_populates="medicine",
        cascade="all, delete-orphan",
    )
