from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from cache_service import models  # noqa: F401 ensures models are registered on Base.metadata
from cache_service.api.routes.payloads import router as payloads_router
from cache_service.db.base import Base
from cache_service.db.session import engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Cache Service", version="1.0.0", lifespan=lifespan)

app.include_router(payloads_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
