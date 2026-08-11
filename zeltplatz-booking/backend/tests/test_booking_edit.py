from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient


def _make_pitch(client: TestClient, name: str = "Edit Platz") -> int:
    r = client.post(
        "/api/v1/pitches",
        json={
            "name": name,
            "available_from": "2020-01-01",
            "available_to": "2030-12-31",
            "daily_price": 5,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _make_booking(client: TestClient, pitch_id: int, start: date, end: date, **extra) -> dict:
    body = {
        "group_name": extra.get("group_name", "Edit Gruppe"),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "pitch_ids": [pitch_id],
        "persons": extra.get(
            "persons",
            [{"name": "Max", "birth_date": "2000-01-01", "nationality": "AT"}],
        ),
        "notes": extra.get("notes", ""),
    }
    r = client.post("/api/v1/bookings", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_full_edit_allowed_on_arrival_day(client: TestClient):
    pitch_id = _make_pitch(client)
    arrival = date(2026, 8, 8)
    booking = _make_booking(client, pitch_id, arrival, arrival + timedelta(days=3))

    with patch("app.api.bookings.date") as mock_date:
        mock_date.today.return_value = arrival
        r = client.patch(
            f"/api/v1/bookings/{booking['id']}",
            json={
                "group_name": "Geändert",
                "persons": [
                    {"name": "Max", "birth_date": "2000-01-01", "nationality": "AT"},
                    {"name": "Eva", "birth_date": "2010-02-02", "nationality": "DE"},
                ],
            },
        )
    assert r.status_code == 200, r.text
    assert r.json()["group_name"] == "Geändert"
    assert len(r.json()["persons"]) == 2


def test_full_edit_blocked_after_arrival_notes_ok(client: TestClient):
    pitch_id = _make_pitch(client, "Edit Platz 2")
    arrival = date(2026, 8, 8)
    booking = _make_booking(
        client, pitch_id, arrival, arrival + timedelta(days=2), notes="alt"
    )

    with patch("app.api.bookings.date") as mock_date:
        mock_date.today.return_value = arrival + timedelta(days=1)

        blocked = client.patch(
            f"/api/v1/bookings/{booking['id']}",
            json={"group_name": "Zu spät"},
        )
        assert blocked.status_code == 409

        notes = client.patch(
            f"/api/v1/bookings/{booking['id']}",
            json={"notes": "neu"},
        )
    assert notes.status_code == 200, notes.text
    assert notes.json()["notes"] == "neu"
    assert notes.json()["group_name"] == "Edit Gruppe"


def test_available_pitches_exclude_own_booking(client: TestClient):
    pitch_id = _make_pitch(client, "Edit Platz 3")
    booking = _make_booking(
        client, pitch_id, date(2026, 7, 1), date(2026, 7, 5)
    )
    without = client.get(
        "/api/v1/pitches/available",
        params={"start": "2026-07-01", "end": "2026-07-05"},
    )
    assert without.json() == []

    with_exclude = client.get(
        "/api/v1/pitches/available",
        params={
            "start": "2026-07-01",
            "end": "2026-07-05",
            "exclude_booking_id": booking["id"],
        },
    )
    assert with_exclude.status_code == 200
    assert any(p["id"] == pitch_id for p in with_exclude.json())
