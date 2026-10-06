from cache_service.services.transformer import transform


def test_transform_is_deterministic():
    assert transform("hello") == transform("hello")


def test_transform_changes_input():
    assert transform("hello") != "hello"
