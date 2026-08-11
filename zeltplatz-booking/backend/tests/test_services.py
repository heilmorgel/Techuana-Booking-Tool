from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models import Booking, BookingService, Service, ServiceGroup
from app.services.service_availability import peak_usage


def _pitch(client: TestClient, name: str = "Platz Services") -> int:
    r = client.post(
        "/api/v1/pitches",
        json={"name": name, "available_from": "2026-06-01", "available_to": "2026-08-31"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _service(client: TestClient, qty: int = 10) -> int:
    g = client.post("/api/v1/service-groups", json={"name": "Mobiliar"})
    assert g.status_code == 201, g.text
    s = client.post(
        "/api/v1/services",
        json={"name": "Festbankgarnituren", "group_id": g.json()["id"], "available_quantity": qty},
    )
    assert s.status_code == 201, s.text
    return s.json()["id"]


def test_service_overbook_warns_but_saves(client: TestClient):
    pitch_id = _pitch(client)
    service_id = _service(client, qty=10)

    base_persons = [{"name": "A", "birth_date": "2010-01-01", "nationality": "AT"}]
    first = client.post(
        "/api/v1/bookings",
        json={
            "group_name": "Gruppe A",
            "start_date": "2026-07-10",
            "end_date": "2026-07-15",
            "pitch_ids": [pitch_id],
            "persons": base_persons,
            "services": [{"service_id": service_id, "quantity": 6}],
        },
    )
    assert first.status_code == 201, first.text
    assert first.json()["warnings"] == []
    assert first.json()["services"][0]["quantity"] == 6

    pitch2 = _pitch(client, name="Platz Services 2")

    second = client.post(
        "/api/v1/bookings",
        json={
            "group_name": "Gruppe B",
            "start_date": "2026-07-12",
            "end_date": "2026-07-18",
            "pitch_ids": [pitch2],
            "persons": base_persons,
            "services": [{"service_id": service_id, "quantity": 5}],
        },
    )
    assert second.status_code == 201, second.text
    assert len(second.json()["warnings"]) == 1
    assert "Festbankgarnituren" in second.json()["warnings"][0]


def test_service_no_overlap_no_warning(client: TestClient):
    pitch_id = _pitch(client)
    service_id = _service(client, qty=10)
    persons = [{"name": "A", "birth_date": "2010-01-01", "nationality": "AT"}]

    client.post(
        "/api/v1/bookings",
        json={
            "group_name": "A",
            "start_date": "2026-07-01",
            "end_date": "2026-07-05",
            "pitch_ids": [pitch_id],
            "persons": persons,
            "services": [{"service_id": service_id, "quantity": 6}],
        },
    )
    pitch2 = _pitch(client, name="Platz B")
    r = client.post(
        "/api/v1/bookings",
        json={
            "group_name": "B",
            "start_date": "2026-07-05",
            "end_date": "2026-07-10",
            "pitch_ids": [pitch2],
            "persons": persons,
            "services": [{"service_id": service_id, "quantity": 5}],
        },
    )
    assert r.status_code == 201
    assert r.json()["warnings"] == []


def test_delete_group_with_services_blocked(client: TestClient):
    g = client.post("/api/v1/service-groups", json={"name": "Technik"}).json()
    client.post(
        "/api/v1/services",
        json={"name": "Strom", "group_id": g["id"], "available_quantity": 2},
    )
    r = client.delete(f"/api/v1/service-groups/{g['id']}")
    assert r.status_code == 409


def test_peak_usage_unit():
    db = SessionLocal()
    try:
        group = ServiceGroup(name="G")
        db.add(group)
        db.flush()
        service = Service(name="S", group_id=group.id, available_quantity=10)
        db.add(service)
        db.flush()
        b1 = Booking(group_name="1", start_date=date(2026, 7, 1), end_date=date(2026, 7, 5))
        b2 = Booking(group_name="2", start_date=date(2026, 7, 3), end_date=date(2026, 7, 8))
        db.add_all([b1, b2])
        db.flush()
        db.add_all(
            [
                BookingService(
                    booking_id=b1.id,
                    service_id=service.id,
                    quantity=4,
                    start_date=date(2026, 7, 1),
                    end_date=date(2026, 7, 5),
                ),
                BookingService(
                    booking_id=b2.id,
                    service_id=service.id,
                    quantity=3,
                    start_date=date(2026, 7, 3),
                    end_date=date(2026, 7, 8),
                ),
            ]
        )
        db.commit()
        assert peak_usage(db, service.id, date(2026, 7, 1), date(2026, 7, 10)) == 7
        assert peak_usage(db, service.id, date(2026, 7, 1), date(2026, 7, 3)) == 4
    finally:
        db.close()
