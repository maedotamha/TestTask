from sqlalchemy import select
from sqlalchemy.orm import Session

from cache_service.models.cache_entry import CacheEntry


class CacheRepository:
    """Database access for the cache_entries table."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_text(self, input_text: str) -> CacheEntry | None:
        stmt = select(CacheEntry).where(CacheEntry.input_text == input_text)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, input_text: str, transformed_text: str) -> CacheEntry:
        entry = CacheEntry(input_text=input_text, transformed_text=transformed_text)
        self.db.add(entry)
        self.db.flush()
        return entry
