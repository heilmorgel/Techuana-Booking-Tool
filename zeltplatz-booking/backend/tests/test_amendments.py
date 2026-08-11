from __future__ import annotations

from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient


def _pitch(client: TestClient, name: str = "Amend Platz") -> int:
    r = client.post(
        "/api/v1/pitches",
        json={
            "name": name,
            "available_from": "2020-01-01",
            "available_to": "2030-12-31",
            "daily_price": 10,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _booking(client: TestClient, pitch_id: int, start: date, end: date, **extra) -> dict:
    body = {
        "group_name": extra.get("group_name", "Amend Gruppe"),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "pitch_ids": [pitch_id],
        "persons": extra.get(
            "persons",
            [{"name": "Max", "birth_date": "2000-01-01", "nationality": "AT"}],
        ),
        "services": extra.get("services", []),
        "notes": "",
    }
    r = client.post("/api/v1/bookings", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_amend_remove_pitch_and_history(client: TestClient):
    p1 = _pitch(client, "A1")
    p2 = client.post(
        "/api/v1/pitches",
        json={
            "name": "A2",
            "available_from": "2020-01-01",
            "available_to": "2030-12-31",
            "daily_price": 10,
        },
    ).json()["id"]
    start = date(2026, 7, 1)
    end = date(2026, 7, 10)
    booking = client.post(
        "/api/v1/bookings",
        json={
            "group_name": "Zwei Plätze",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "pitch_ids": [p1, p2],
            "persons": [],
        },
    ).json()

    effective = date(2026, 7, 5)
    with patch("app.api.bookings.date") as mock_date:
        mock_date.today.return_value = effective
        r = client.post(
            f"/api/v1/bookings/{booking['id']}/amend",
            json={
                "effective_date": effective.isoformat(),
                "end_date": end.isoformat(),
                "pitch_ids": [p1],
                "persons": [],
                "services": [],
            },
        )
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data["amendments"]) == 1
    assert data["amendments"][0]["effective_date"] == effective.isoformat()
    diff = __import__("json").loads(data["amendments"][0]["diff_json"])
    assert any(line.startswith("− Platz") for line in diff["changes"])

    inv = client.get(f"/api/v1/bookings/{booking['id']}/invoice").json()
    # p1: 9 nights * 10 = 90; p2: 4 nights * 10 = 40; total 130
    assert inv["total"] == 130.0
    labels = " ".join(line["label"] for line in inv["lines"])
    assert "2026-07-01" in labels and "2026-07-05" in labels


def test_amend_service_qty_change(client: TestClient):
    pitch_id = _pitch(client, "Svc Platz")
    g = client.post("/api/v1/service-groups", json={"name": "G1"}).json()
    svc = client.post(
        "/api/v1/services",
        json={"name": "Zelt", "group_id": g["id"], "available_quantity": 5, "daily_price": 2},
    ).json()
    start = date(2026, 8, 1)
    end = date(2026, 8, 8)
    booking = _booking(
        client,
        pitch_id,
        start,
        end,
        persons=[],
        services=[{"service_id": svc["id"], "quantity": 2}],
    )
    effective = date(2026, 8, 4)
    with patch("app.api.bookings.date") as mock_date:
        mock_date.today.return_value = effective
        r = client.post(
            f"/api/v1/bookings/{booking['id']}/amend",
            json={
                "effective_date": effective.isoformat(),
                "end_date": end.isoformat(),
                "pitch_ids": [pitch_id],
                "persons": [],
                "services": [{"service_id": svc["id"], "quantity": 1}],
            },
        )
    assert r.status_code == 200, r.text
    services = r.json()["services"]
    assert len(services) == 2
    inv = client.get(f"/api/v1/bookings/{booking['id']}/invoice").json()
    service_lines = [l for l in inv["lines"] if l["category"] == "service"]
    assert len(service_lines) == 2


def test_amend_blocked_after_end(client: TestClient):
    pitch_id = _pitch(client, "Ende Platz")
    start = date(2026, 6, 1)
    end = date(2026, 6, 5)
    booking = _booking(client, pitch_id, start, end, persons=[])
    with patch("app.api.bookings.date") as mock_date:
        mock_date.today.return_value = end
        r = client.post(
            f"/api/v1/bookings/{booking['id']}/amend",
            json={
                "effective_date": start.isoformat(),
                "end_date": end.isoformat(),
                "pitch_ids": [pitch_id],
                "persons": [],
                "services": [],
            },
        )
    assert r.status_code == 409


def test_amend_shorten_end_date(client: TestClient):
    pitch_id = _pitch(client, "Kurz Platz")
    start = date(2026, 9, 1)
    end = date(2026, 9, 10)
    booking = _booking(client, pitch_id, start, end, persons=[])
    effective = date(2026, 9, 3)
    new_end = date(2026, 9, 6)
    with patch("app.api.bookings.date") as mock_date:
        mock_date.today.return_value = effective
        r = client.post(
            f"/api/v1/bookings/{booking['id']}/amend",
            json={
                "effective_date": effective.isoformat(),
                "end_date": new_end.isoformat(),
                "pitch_ids": [pitch_id],
                "persons": [],
                "services": [],
            },
        )
    assert r.status_code == 200, r.text
    assert r.json()["end_date"] == new_end.isoformat()
    segs = r.json()["pitch_segments"]
    assert all(s["end_date"] <= new_end.isoformat() for s in segs)


def test_smoke_amend_history_invoice_dates(client: TestClient):
    pitch_id = _pitch(client, "Smoke Amend")
    start = date(2026, 10, 1)
    end = date(2026, 10, 12)
    booking = _booking(client, pitch_id, start, end, persons=[])
    effective = date(2026, 10, 5)
    with patch("app.api.bookings.date") as mock_date:
        mock_date.today.return_value = effective
        amended = client.post(
            f"/api/v1/bookings/{booking['id']}/amend",
            json={
                "effective_date": effective.isoformat(),
                "end_date": "2026-10-10",
                "pitch_ids": [pitch_id],
                "persons": [
                    {
                        "name": "Neu",
                        "birth_date": "1990-01-01",
                        "nationality": "AT",
                        "start_date": effective.isoformat(),
                        "end_date": "2026-10-10",
                    }
                ],
                "services": [],
            },
        )
    assert amended.status_code == 200, amended.text
    assert amended.json()["amendments"]
    hist = client.get(f"/api/v1/bookings/{booking['id']}/amendments")
    assert hist.status_code == 200 and len(hist.json()) >= 1
    inv = client.get(f"/api/v1/bookings/{booking['id']}/invoice").json()
    assert all(line.get("start_date") and line.get("end_date") for line in inv["lines"])
    pdf = client.get(f"/api/v1/bookings/{booking['id']}/invoice.pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
