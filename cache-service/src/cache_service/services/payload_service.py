import hashlib
import json

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from cache_service.models.payload import Payload
from cache_service.repositories.cache_repository import CacheRepository
from cache_service.repositories.payload_repository import PayloadRepository
from cache_service.services.transformer import transform

_MAX_CACHE_ATTEMPTS = 3


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

        transformed = self._resolve_transformations([*list_1, *list_2])
        output: list[str] = []
        for first, second in zip(list_1, list_2, strict=True):
            output.append(transformed[first])
            output.append(transformed[second])

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

    def _resolve_transformations(self, texts: list[str]) -> dict[str, str]:
        """Return {input: transformed} for every unique text, calling the transformer only on cache misses."""
        unique_texts = set(texts)
        resolved: dict[str, str] = {}

        for _ in range(_MAX_CACHE_ATTEMPTS):
            cached = self.cache_repo.get_many_by_text(unique_texts - resolved.keys())
            resolved.update({text: entry.transformed_text for text, entry in cached.items()})

            missing = unique_texts - resolved.keys()
            if not missing:
                return resolved

            new_values = {text: transform(text) for text in missing}
            try:
                for text, value in new_values.items():
                    self.cache_repo.create(text, value)
                self.db.commit()
            except IntegrityError:
                # A concurrent request inserted one of these texts first; reread and retry only the rest.
                self.db.rollback()
                continue
            resolved.update(new_values)
            return resolved

        raise RuntimeError("could not populate the transformation cache after repeated conflicts")
