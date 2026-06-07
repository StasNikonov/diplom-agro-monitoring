"""CRUD tests for /fields endpoint."""
import pytest

BOUNDARY = {
    "type": "Polygon",
    "coordinates": [[[30.0, 50.0], [30.1, 50.0], [30.1, 50.1], [30.0, 50.1], [30.0, 50.0]]],
}

PAYLOAD = {"name": "Test Field", "area_ha": 12.5, "boundary": BOUNDARY}


def test_create_field(authed_client):
    r = authed_client.post("/fields", json=PAYLOAD)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Test Field"
    assert data["area_ha"] == 12.5
    assert data["boundary"]["type"] == "Polygon"


def test_list_fields(authed_client):
    authed_client.post("/fields", json=PAYLOAD)
    r = authed_client.get("/fields")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert any(f["name"] == "Test Field" for f in r.json())


def test_get_field(authed_client):
    created = authed_client.post("/fields", json=PAYLOAD).json()
    r = authed_client.get(f"/fields/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_get_field_not_found(authed_client):
    r = authed_client.get("/fields/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_create_field_requires_auth(client):
    r = client.post("/fields", json=PAYLOAD)
    assert r.status_code == 403
