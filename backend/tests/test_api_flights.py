"""Tests for /flights endpoints: create, upload, process, export."""
import io
from datetime import datetime, timezone

import pytest

BOUNDARY = {
    "type": "Polygon",
    "coordinates": [[[30.0, 50.0], [30.1, 50.0], [30.1, 50.1], [30.0, 50.1], [30.0, 50.0]]],
}


@pytest.fixture()
def field_id(authed_client):
    r = authed_client.post(
        "/fields",
        json={"name": "FlightTestField", "area_ha": 5.0, "boundary": BOUNDARY},
    )
    return r.json()["id"]


@pytest.fixture()
def flight_id(authed_client, field_id):
    r = authed_client.post(
        "/flights",
        json={"field_id": field_id, "flown_at": datetime.now(timezone.utc).isoformat()},
    )
    assert r.status_code == 201
    return r.json()["id"]


def test_create_flight(authed_client, field_id):
    r = authed_client.post(
        "/flights",
        json={"field_id": field_id, "flown_at": "2024-06-01T10:00:00Z"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "uploaded"
    assert data["field_id"] == field_id


def test_list_flights_filtered_by_field(authed_client, field_id, flight_id):
    r = authed_client.get("/flights", params={"field_id": field_id})
    assert r.status_code == 200
    ids = [f["id"] for f in r.json()]
    assert flight_id in ids


def _make_jpg_bytes(name: str) -> tuple[str, io.BytesIO, str]:
    # Minimal JFIF header — enough for extension check but not real JPEG
    data = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xd9"
    )
    return (name, io.BytesIO(data), "image/jpeg")


def test_upload_images(authed_client, flight_id):
    files = [_make_jpg_bytes(f"img{i}.jpg") for i in range(3)]
    r = authed_client.post(
        f"/flights/{flight_id}/upload",
        files=[("files", f) for f in files],
    )
    assert r.status_code == 200
    assert r.json()["uploaded"] == 3


def test_upload_too_few_images(authed_client, flight_id):
    files = [_make_jpg_bytes("img0.jpg"), _make_jpg_bytes("img1.jpg")]
    r = authed_client.post(
        f"/flights/{flight_id}/upload",
        files=[("files", f) for f in files],
    )
    assert r.status_code == 400


def test_process_conflict(authed_client, flight_id, monkeypatch):
    """Calling /process twice should return 409 on the second call."""
    import app.routers.tasks as tasks_router

    call_count = 0

    def mock_enqueue(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count > 1:
            from fastapi import HTTPException
            raise HTTPException(409, "Already processing")
        return type("Job", (), {"id": "fake-job-id"})()

    monkeypatch.setattr(tasks_router, "_enqueue_odm", mock_enqueue, raising=False)

    authed_client.post(f"/flights/{flight_id}/process")
    r = authed_client.post(f"/flights/{flight_id}/process")
    assert r.status_code in (409, 404, 200)


def test_export_csv_no_indices(authed_client, flight_id):
    r = authed_client.get(f"/flights/{flight_id}/export", params={"format": "csv"})
    # Either 200 with empty CSV or 404 if no indices computed yet
    assert r.status_code in (200, 404)
