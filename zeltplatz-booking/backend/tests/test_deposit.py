from __future__ import annotations

from fastapi.testclient import TestClient


def _default_profile_id(client: TestClient) -> int:
    profiles = client.get("/api/v1/price-profiles").json()
    return next(p["id"] for p in profiles if p["is_default"])


def test_deposit_calculation_and_invoice_deduction(client: TestClient):
    profile_id = _default_profile_id(client)
    client.patch(f"/api/v1/price-profiles/{profile_id}", json={"deposit": 30})
    other = client.post(
        "/api/v1/price-profiles",
        json={"name": "Ermaessigt Deposit", "deposit": 15, "sort_order": 2},
    )
    assert other.status_code == 201, other.text
    other_id = other.json()["id"]

    pitch_a = client.post(
        "/api/v1/pitches",
        json={
            "name": "Platz Deposit A",
            "available_from": "2026-06-01",
            "available_to": "2026-08-31",
            "daily_price": 20,
            "deposit": 50,
        },
    )
    assert pitch_a.status_code == 201, pitch_a.text
    pitch_b = client.post(
        "/api/v1/pitches",
        json={
            "name": "Platz Deposit B",
            "available_from": "2026-06-01",
            "available_to": "2026-08-31",
            "daily_price": 10,
            "deposit": 40,
        },
    ).json()

    group = client.post("/api/v1/service-groups", json={"name": "Deposit Group"})
    assert group.status_code == 201, group.text
    svc = client.post(
        "/api/v1/services",
        json={
            "name": "Tisch Deposit",
            "group_id": group.json()["id"],
            "available_quantity": 10,
            "daily_price": 1,
            "deposit": 5,
        },
    )
    assert svc.status_code == 201, svc.text

    booking = client.post(
        "/api/v1/bookings",
        json={
            "group_name": "Deposit Test",
            "start_date": "2026-07-01",
            "end_date": "2026-07-03",
            "pitch_ids": [pitch_a.json()["id"], pitch_b["id"]],
            "services": [{"service_id": svc.json()["id"], "quantity": 3}],
            "persons": [
                {
                    "name": "Anna",
                    "birth_date": "2000-01-01",
                    "nationality": "AT",
                    "price_profile_id": profile_id,
                },
                {
                    "name": "Ben",
                    "birth_date": "2001-01-01",
                    "nationality": "AT",
                    "price_profile_id": profile_id,
                },
                {
                    "name": "Cara",
                    "birth_date": "2002-01-01",
                    "nationality": "AT",
                    "price_profile_id": other_id,
                },
            ],
        },
    )
    assert booking.status_code == 201, booking.text
    data = booking.json()
    # pitches 50+40 + service 5*3 + profiles 30+15 (once each) = 150
    assert data["deposit_due"] == 150.0
    assert data["deposit_paid_at"] is None

    bid = data["id"]
    inv = client.get(f"/api/v1/bookings/{bid}/invoice").json()
    assert inv["deposit_due"] == 150.0
    assert all(l["category"] != "deposit" for l in inv["lines"])
    total_before = inv["total"]

    toggled = client.post(f"/api/v1/bookings/{bid}/deposit/toggle")
    assert toggled.status_code == 200, toggled.text
    assert toggled.json()["deposit_due"] == 150.0
    assert toggled.json()["deposit_paid_at"] is not None

    inv2 = client.get(f"/api/v1/bookings/{bid}/invoice").json()
    assert inv2["total"] == total_before - 150.0
    deposit_lines = [l for l in inv2["lines"] if l["category"] == "deposit"]
    assert len(deposit_lines) == 1
    assert deposit_lines[0]["amount"] == -150.0
    assert "bezahlt am" in deposit_lines[0]["label"]

    toggled_back = client.post(f"/api/v1/bookings/{bid}/deposit/toggle")
    assert toggled_back.status_code == 200
    assert toggled_back.json()["deposit_paid_at"] is None
    inv3 = client.get(f"/api/v1/bookings/{bid}/invoice").json()
    assert inv3["total"] == total_before
    assert all(l["category"] != "deposit" for l in inv3["lines"])
