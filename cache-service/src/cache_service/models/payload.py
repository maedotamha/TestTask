from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from cache_service.db.base import Base


class Payload(Base):
    """One record per unique generated payload."""

    __tablename__ = "payloads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    request_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    output: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
