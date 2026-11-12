import uuid
from typing import Any, List
from sqlalchemy import ForeignKey, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Recommendation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Persisted recommendation results generated for a healthcare request."""
    __tablename__ = "recommendations"

    request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("healthcare_requests.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    items_payload: Mapped[List[dict[str, Any]]] = mapped_column(JSON, nullable=False)
