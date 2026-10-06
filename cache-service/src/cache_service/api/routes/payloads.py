from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from cache_service.db.session import get_db
from cache_service.repositories.payload_repository import PayloadRepository
from cache_service.schemas.payload import PayloadCreatedResponse, PayloadRequest, PayloadResponse
from cache_service.services.payload_service import PayloadService

DbSession = Annotated[Session, Depends(get_db)]

router = APIRouter(prefix="/payload", tags=["payload"])

OUTPUT_SEPARATOR = ", "


@router.post("", response_model=PayloadCreatedResponse, status_code=201)
def create_payload(request: PayloadRequest, db: DbSession) -> PayloadCreatedResponse:
    payload = PayloadService(db).get_or_create_payload(request.list_1, request.list_2)
    return PayloadCreatedResponse(id=payload.id, message="Payload generated")


@router.get("/{payload_id}", response_model=PayloadResponse)
def get_payload(payload_id: str, db: DbSession) -> PayloadResponse:
    payload = PayloadRepository(db).get_by_id(payload_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Payload not found")
    return PayloadResponse(output=OUTPUT_SEPARATOR.join(payload.output))
