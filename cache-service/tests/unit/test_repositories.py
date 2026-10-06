import pytest
from sqlalchemy.exc import IntegrityError

from cache_service.repositories.cache_repository import CacheRepository
from cache_service.repositories.payload_repository import PayloadRepository


def test_cache_get_returns_none_on_miss_and_entry_on_hit(db_session):
    repo = CacheRepository(db_session)
    assert repo.get_by_text("a") is None

    repo.create("a", "A")
    assert repo.get_by_text("a").transformed_text == "A"


def test_cache_empty_string_result_is_a_hit_not_a_miss(db_session):
    repo = CacheRepository(db_session)
    repo.create("x", "")

    entry = repo.get_by_text("x")
    assert entry is not None
    assert entry.transformed_text == ""


def test_cache_get_many_returns_only_existing_keys(db_session):
    repo = CacheRepository(db_session)
    repo.create("a", "A")
    repo.create("b", "B")

    found = repo.get_many_by_text(["a", "b", "missing", "a"])

    assert {k: v.transformed_text for k, v in found.items()} == {"a": "A", "b": "B"}
    assert repo.get_many_by_text([]) == {}


def test_cache_create_duplicate_raises_and_session_recovers_after_rollback(db_session):
    repo = CacheRepository(db_session)
    repo.create("a", "A")
    db_session.commit()

    with pytest.raises(IntegrityError):
        repo.create("a", "OTHER")
    db_session.rollback()

    assert repo.get_by_text("a").transformed_text == "A"


def test_payload_lookup_by_hash_and_id(db_session):
    repo = PayloadRepository(db_session)
    created = repo.create("h" * 64, ["A", "B"])

    assert repo.get_by_hash("h" * 64).id == created.id
    assert repo.get_by_id(created.id).output == ["A", "B"]
    assert repo.get_by_hash("z" * 64) is None
    assert repo.get_by_id("does-not-exist") is None


def test_payload_create_duplicate_hash_raises_and_session_recovers(db_session):
    repo = PayloadRepository(db_session)
    first = repo.create("h" * 64, ["A"])
    db_session.commit()

    with pytest.raises(IntegrityError):
        repo.create("h" * 64, ["B"])
    db_session.rollback()

    assert repo.get_by_hash("h" * 64).id == first.id
