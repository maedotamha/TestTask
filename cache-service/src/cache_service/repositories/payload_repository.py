from sqlalchemy import select
from sqlalchemy.orm import Session

from cache_service.models.payload import Payload


class PayloadRepository:
    """Database access for the payloads table."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_hash(self, request_hash: str) -> Payload | None:
        stmt = select(Payload).where(Payload.request_hash == request_hash)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_id(self, payload_id: str) -> Payload | None:
        return self.db.get(Payload, payload_id)

    def create(self, request_hash: str, output: list[str]) -> Payload:
        payload = Payload(request_hash=request_hash, output=output)
        self.db.add(payload)
        self.db.flush()
        return payload
