from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.models import Pitch
from app.services.availability import intervals_overlap, pitch_covers_range


def test_intervals_overlap():
    assert intervals_overlap(date(2026, 7, 1), date(2026, 7, 5), date(2026, 7, 4), date(2026, 7, 10))
    assert not intervals_overlap(date(2026, 7, 1), date(2026, 7, 5), date(2026, 7, 5), date(2026, 7, 10))


def test_pitch_covers_range():
    pitch = Pitch(
        name="A",
        available_from=date(2026, 6, 1),
        available_to=date(2026, 8, 31),
    )
    assert pitch_covers_range(pitch, date(2026, 7, 1), date(2026, 7, 8))
    assert pitch_covers_range(pitch, date(2026, 8, 31), date(2026, 9, 1))
    assert not pitch_covers_range(pitch, date(2026, 5, 20), date(2026, 6, 5))


def test_health(client: TestClient):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["version"] == "0.1.5"


def test_create_pitch_and_booking_conflict(client: TestClient):
    season_from = "2026-06-01"
    season_to = "2026-08-31"
    r = client.post(
        "/api/v1/pitches",
        json={"name": "Platz 1", "available_from": season_from, "available_to": season_to},
    )
    assert r.status_code == 201
    pitch_id = r.json()["id"]

    booking = {
        "group_name": "Stamm Adler",
        "start_date": "2026-07-10",
        "end_date": "2026-07-15",
        "pitch_ids": [pitch_id],
        "persons": [
            {"name": "Max Muster", "birth_date": "2012-05-01", "nationality": "AT"},
            {"name": "Eva Beispiel", "birth_date": "2011-03-12", "nationality": "DE"},
        ],
    }
    r = client.post("/api/v1/bookings", json=booking)
    assert r.status_code == 201, r.text

    conflict = dict(booking)
    conflict["group_name"] = "Stamm Fuchs"
    conflict["start_date"] = "2026-07-14"
    conflict["end_date"] = "2026-07-18"
    r = client.post("/api/v1/bookings", json=conflict)
    assert r.status_code == 409

    available = client.get("/api/v1/pitches/available", params={"start": "2026-07-10", "end": "2026-07-15"})
    assert available.status_code == 200
    assert available.json() == []

    free = client.get("/api/v1/pitches/available", params={"start": "2026-07-15", "end": "2026-07-20"})
    assert free.status_code == 200
    assert len(free.json()) == 1


def test_delete_pitch_with_booking_blocked(client: TestClient):
    r = client.post(
        "/api/v1/pitches",
        json={"name": "Platz 2", "available_from": "2026-06-01", "available_to": "2026-08-31"},
    )
    pitch_id = r.json()["id"]
    client.post(
        "/api/v1/bookings",
        json={
            "group_name": "Gruppe",
            "start_date": "2026-07-01",
            "end_date": "2026-07-03",
            "pitch_ids": [pitch_id],
            "persons": [{"name": "A", "birth_date": "2010-01-01", "nationality": "AT"}],
        },
    )
    r = client.delete(f"/api/v1/pitches/{pitch_id}")
    assert r.status_code == 409
