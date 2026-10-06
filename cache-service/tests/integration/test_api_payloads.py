from cache_service.services.transformer import transform


def test_create_payload_interleaves_transformed_values(client):
    response = client.post("/payloads", json={"list_1": ["hello", "world"], "list_2": ["one", "two"]})
    assert response.status_code == 201
    body = response.json()
    assert body["output"] == [transform("hello"), transform("one"), transform("world"), transform("two")]


def test_duplicate_request_returns_same_id(client):
    payload_body = {"list_1": ["hello", "world"], "list_2": ["one", "two"]}
    first = client.post("/payloads", json=payload_body).json()
    second = client.post("/payloads", json=payload_body).json()
    assert first["id"] == second["id"]


def test_mismatched_lengths_return_422(client):
    response = client.post("/payloads", json={"list_1": ["a"], "list_2": ["a", "b"]})
    assert response.status_code == 422


def test_get_payload_by_id(client):
    created = client.post("/payloads", json={"list_1": ["x"], "list_2": ["y"]}).json()
    response = client.get(f"/payloads/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_unknown_payload_returns_404(client):
    response = client.get("/payloads/does-not-exist")
    assert response.status_code == 404
