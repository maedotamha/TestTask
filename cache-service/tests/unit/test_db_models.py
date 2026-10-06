import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from cache_service.db.base import Base
from cache_service.db.session import make_engine, make_session_factory
from cache_service.models import CacheEntry, Payload


def _unique_columns(engine, table: str) -> set[tuple[str, ...]]:
    insp = inspect(engine)
    uniques = {tuple(u["column_names"]) for u in insp.get_unique_constraints(table)}
    uniques |= {tuple(i["column_names"]) for i in insp.get_indexes(table) if i["unique"]}
    return uniques


def test_models_share_base_metadata():
    assert CacheEntry.metadata is Base.metadata
    assert Payload.metadata is Base.metadata
    assert {"cache_entries", "payloads"} <= set(Base.metadata.tables)


def test_unique_constraints_exist_in_schema(engine):
    assert ("input_text",) in _unique_columns(engine, "cache_entries")
    assert ("request_hash",) in _unique_columns(engine, "payloads")


def test_duplicate_input_text_rejected_and_session_recovers(db_session):
    db_session.add(CacheEntry(input_text="first", transformed_text="FIRST"))
    db_session.commit()

    db_session.add(CacheEntry(input_text="first", transformed_text="OTHER"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    assert db_session.query(CacheEntry).count() == 1


def test_empty_string_is_a_valid_cached_value(db_session):
    db_session.add(CacheEntry(input_text="", transformed_text=""))
    db_session.commit()

    entry = db_session.query(CacheEntry).filter_by(input_text="").one()
    assert entry.transformed_text == ""


def test_duplicate_request_hash_rejected(db_session):
    db_session.add(Payload(request_hash="a" * 64, output=["X"]))
    db_session.commit()

    db_session.add(Payload(request_hash="a" * 64, output=["Y"]))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    assert db_session.query(Payload).count() == 1


def test_payload_gets_distinct_stable_ids_and_roundtrips_output(db_session):
    first = Payload(request_hash="a" * 64, output=["A", "B"])
    second = Payload(request_hash="b" * 64, output=["C"])
    db_session.add_all([first, second])
    db_session.commit()

    assert first.id and second.id and first.id != second.id
    db_session.expire_all()
    assert db_session.get(Payload, first.id).output == ["A", "B"]


def test_make_engine_uses_given_url():
    eng = make_engine("sqlite:///:memory:")
    assert eng.dialect.name == "sqlite"
    assert eng.url.database == ":memory:"
    eng.dispose()


def test_session_factory_sessions_are_independent_and_closable():
    eng = make_engine("sqlite:///:memory:")
    factory = make_session_factory(eng)
    one, two = factory(), factory()
    assert one is not two
    one.close()
    two.close()
    eng.dispose()
