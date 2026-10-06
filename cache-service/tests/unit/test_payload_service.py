import pytest

from cache_service.services import payload_service as payload_service_module
from cache_service.services.payload_service import PayloadService, compute_request_hash


def test_request_hash_distinguishes_list_order_and_position():
    h1 = compute_request_hash(["a", "b"], ["c", "d"])
    h2 = compute_request_hash(["b", "a"], ["c", "d"])
    h3 = compute_request_hash(["c", "d"], ["a", "b"])
    assert len({h1, h2, h3}) == 3


def test_cache_is_reused_across_payloads(db_session, monkeypatch):
    calls: list[str] = []

    def fake_transform(text: str) -> str:
        calls.append(text)
        return text.upper()

    monkeypatch.setattr(payload_service_module, "transform", fake_transform)

    service = PayloadService(db_session)
    service.get_or_create_payload(["hello", "world"], ["one", "two"])
    service.get_or_create_payload(["hello", "there"], ["one", "three"])

    # "hello" and "one" are shared between both requests; the transformer
    # should only run once per unique string.
    assert calls.count("hello") == 1
    assert calls.count("one") == 1
    assert calls.count("world") == 1
    assert calls.count("there") == 1
    assert calls.count("two") == 1
    assert calls.count("three") == 1


def test_duplicate_requests_return_same_payload_id(db_session):
    service = PayloadService(db_session)
    first = service.get_or_create_payload(["hello", "world"], ["one", "two"])
    second = service.get_or_create_payload(["hello", "world"], ["one", "two"])
    assert first.id == second.id


def test_different_requests_get_different_payload_ids(db_session):
    service = PayloadService(db_session)
    first = service.get_or_create_payload(["hello", "world"], ["one", "two"])
    second = service.get_or_create_payload(["hello", "there"], ["one", "three"])
    assert first.id != second.id


def test_mismatched_lengths_raise_value_error(db_session):
    service = PayloadService(db_session)
    with pytest.raises(ValueError):
        service.get_or_create_payload(["a"], ["b", "c"])
