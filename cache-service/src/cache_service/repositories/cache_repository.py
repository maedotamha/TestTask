from collections.abc import Collection

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

    def get_many_by_text(self, input_texts: Collection[str]) -> dict[str, CacheEntry]:
        """Fetch cached entries for many strings in one query, keyed by input text.

        Missing strings are simply absent from the result, so an empty cached
        transformation is distinguishable from a cache miss.
        """
        if not input_texts:
            return {}
        stmt = select(CacheEntry).where(CacheEntry.input_text.in_(set(input_texts)))
        return {entry.input_text: entry for entry in self.db.execute(stmt).scalars()}

    def create(self, input_text: str, transformed_text: str) -> CacheEntry:
        """Insert and flush without committing.

        Raises IntegrityError if input_text already exists; the caller owns the
        transaction and must roll back before reusing the session.
        """
        entry = CacheEntry(input_text=input_text, transformed_text=transformed_text)
        self.db.add(entry)
        self.db.flush()
        return entry
