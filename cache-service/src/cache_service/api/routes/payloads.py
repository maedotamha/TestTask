from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from cache_service.db.session import get_db
from cache_service.repositories.payload_repository import PayloadRepository
from cache_service.schemas.payload import PayloadRequest, PayloadResponse
from cache_service.services.payload_service import PayloadService

router = APIRouter(prefix="/payloads", tags=["payloads"])


@router.post("", response_model=PayloadResponse, status_code=201)
def create_payload(request: PayloadRequest, db: Session = Depends(get_db)) -> PayloadResponse:
    service = PayloadService(db)
    try:
        payload = service.get_or_create_payload(request.list_1, request.list_2)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return PayloadResponse.model_validate(payload)


@router.get("/{payload_id}", response_model=PayloadResponse)
def get_payload(payload_id: str, db: Session = Depends(get_db)) -> PayloadResponse:
    payload = PayloadRepository(db).get_by_id(payload_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Payload not found")
    return PayloadResponse.model_validate(payload)
