from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from cache_service.db.base import Base


class Payload(Base):
    """One record per unique generated payload."""

    __tablename__ = "payloads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    request_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    output: Mapped[list] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
