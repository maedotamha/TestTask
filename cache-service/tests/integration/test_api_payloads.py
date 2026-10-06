SAMPLE = {
    "list_1": ["first string", "second string", "third string"],
    "list_2": ["other string", "another string", "last string"],
}
SAMPLE_OUTPUT = "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING, THIRD STRING, LAST STRING"


def test_post_then_get_returns_sample_output(client):
    created = client.post("/payload", json=SAMPLE)
    assert created.status_code == 201
    assert created.json()["id"]
    assert created.json()["message"]

    response = client.get(f"/payload/{created.json()['id']}")
    assert response.status_code == 200
    assert response.json() == {"output": SAMPLE_OUTPUT}


def test_identical_posts_return_same_id(client):
    first = client.post("/payload", json=SAMPLE).json()
    second = client.post("/payload", json=SAMPLE).json()
    assert first["id"] == second["id"]


def test_swapped_lists_get_a_different_id(client):
    first = client.post("/payload", json=SAMPLE).json()
    swapped = {"list_1": SAMPLE["list_2"], "list_2": SAMPLE["list_1"]}
    assert client.post("/payload", json=swapped).json()["id"] != first["id"]


def test_cached_strings_are_reused_across_payloads(client, monkeypatch):
    from cache_service.services import payload_service

    calls: list[str] = []
    real = payload_service.transform
    monkeypatch.setattr(payload_service, "transform", lambda t: calls.append(t) or real(t))

    client.post("/payload", json={"list_1": ["a", "b"], "list_2": ["c", "d"]})
    client.post("/payload", json={"list_1": ["a", "x"], "list_2": ["c", "d"]})

    assert sorted(calls) == ["a", "b", "c", "d", "x"]


def test_mismatched_lengths_return_422(client):
    response = client.post("/payload", json={"list_1": ["a"], "list_2": ["a", "b"]})
    assert response.status_code == 422


def test_missing_field_and_non_string_items_return_422(client):
    assert client.post("/payload", json={"list_1": ["a"]}).status_code == 422
    assert client.post("/payload", json={"list_1": [1], "list_2": ["a"]}).status_code == 422


def test_get_unknown_payload_returns_404(client):
    response = client.get("/payload/does-not-exist")
    assert response.status_code == 404


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
