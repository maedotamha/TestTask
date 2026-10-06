from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from cache_service.config import settings


def make_engine(database_url: str, echo: bool = False) -> Engine:
    """Build an engine for the given URL. Creating an engine does not open a connection."""
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, echo=echo, connect_args=connect_args)


def make_session_factory(bind: Engine) -> sessionmaker[Session]:
    """Sessions never autoflush or expire on commit; callers own commit and rollback."""
    return sessionmaker(bind=bind, autoflush=False, expire_on_commit=False)


engine = make_engine(settings.database_url, settings.echo_sql)
SessionLocal = make_session_factory(engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding one session per request; always closed afterwards.

    Closing a session rolls back any uncommitted transaction. Callers must call
    ``rollback()`` themselves after a failed flush/commit before reusing the session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
