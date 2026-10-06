import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from cache_service import models  # noqa: F401 ensures models are registered on Base.metadata
from cache_service.db.base import Base
from cache_service.db.session import get_db
from cache_service.main import app


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture()
def db_session(engine):
    session_factory = sessionmaker(bind=engine, future=True)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(engine):
    session_factory = sessionmaker(bind=engine, future=True)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # Not using the TestClient as a context manager so the app's "startup"
    # event (which binds to the real engine) never runs during tests.
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()
