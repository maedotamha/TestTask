import hashlib
import json

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from cache_service.models.payload import Payload
from cache_service.repositories.cache_repository import CacheRepository
from cache_service.repositories.payload_repository import PayloadRepository
from cache_service.services.transformer import transform


def compute_request_hash(list_1: list[str], list_2: list[str]) -> str:
    """Fingerprint a request.

    Uses fixed JSON keys and preserves list order so that swapping list_1/list_2
    or reordering either list produces a different hash.
    """
    canonical = json.dumps({"list_1": list(list_1), "list_2": list(list_2)}, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class PayloadService:
    """Orchestrates cache lookups and payload generation/deduplication."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.cache_repo = CacheRepository(db)
        self.payload_repo = PayloadRepository(db)

    def get_or_create_payload(self, list_1: list[str], list_2: list[str]) -> Payload:
        if len(list_1) != len(list_2):
            raise ValueError("list_1 and list_2 must have the same length")

        request_hash = compute_request_hash(list_1, list_2)

        existing = self.payload_repo.get_by_hash(request_hash)
        if existing is not None:
            return existing

        output: list[str] = []
        for first, second in zip(list_1, list_2):
            output.append(self._get_or_create_transformed(first))
            output.append(self._get_or_create_transformed(second))

        try:
            payload = self.payload_repo.create(request_hash, output)
            self.db.commit()
            return payload
        except IntegrityError:
            # A concurrent request committed the same payload first.
            self.db.rollback()
            existing = self.payload_repo.get_by_hash(request_hash)
            if existing is not None:
                return existing
            raise

    def _get_or_create_transformed(self, text: str) -> str:
        entry = self.cache_repo.get_by_text(text)
        if entry is not None:
            return entry.transformed_text

        transformed = transform(text)
        try:
            entry = self.cache_repo.create(text, transformed)
            self.db.commit()
            return entry.transformed_text
        except IntegrityError:
            # A concurrent request inserted the same input_text first.
            self.db.rollback()
            entry = self.cache_repo.get_by_text(text)
            if entry is not None:
                return entry.transformed_text
            raise
