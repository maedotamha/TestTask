from datetime import datetime, timezone

from sqlalchemy import DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from cache_service.db.base import Base


class CacheEntry(Base):
    """One record per unique input string and its transformed result."""

    __tablename__ = "cache_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    input_text: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    transformed_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
