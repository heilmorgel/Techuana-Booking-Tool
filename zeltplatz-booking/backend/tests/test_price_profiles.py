from __future__ import annotations

from fastapi.testclient import TestClient


def _default_profile_id(client: TestClient) -> int:
    profiles = client.get("/api/v1/price-profiles").json()
    assert profiles
    return next(p["id"] for p in profiles if p["is_default"])


def test_default_profile_seeded(client: TestClient):
    profiles = client.get("/api/v1/price-profiles").json()
    assert len(profiles) == 1
    assert profiles[0]["name"] == "Standard"
    assert profiles[0]["is_default"] is True


def test_create_and_set_default_profile(client: TestClient):
    created = client.post(
        "/api/v1/price-profiles",
        json={"name": "Ermäßigt", "is_default": True, "sort_order": 1},
    )
    assert created.status_code == 201, created.text
    assert created.json()["is_default"] is True

    profiles = client.get("/api/v1/price-profiles").json()
    defaults = [p for p in profiles if p["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["name"] == "Ermäßigt"


def test_cannot_delete_last_or_in_use_profile(client: TestClient):
    default_id = _default_profile_id(client)
    assert client.delete(f"/api/v1/price-profiles/{default_id}").status_code == 422

    other = client.post(
        "/api/v1/price-profiles",
        json={"name": "Extra", "is_default": False},
    ).json()
    pitch = client.post(
        "/api/v1/pitches",
        json={
            "name": "Platz Profil",
            "available_from": "2026-06-01",
            "available_to": "2026-08-31",
        },
    ).json()
    booking = client.post(
        "/api/v1/bookings",
        json={
            "group_name": "Mit Profil",
            "start_date": "2026-07-01",
            "end_date": "2026-07-03",
            "pitch_ids": [pitch["id"]],
            "persons": [
                {
                    "name": "Max",
                    "birth_date": "2000-01-01",
                    "nationality": "AT",
                    "price_profile_id": other["id"],
                }
            ],
        },
    )
    assert booking.status_code == 201, booking.text
    assert client.delete(f"/api/v1/price-profiles/{other['id']}").status_code == 409


def test_person_gets_default_profile(client: TestClient):
    default_id = _default_profile_id(client)
    pitch = client.post(
        "/api/v1/pitches",
        json={
            "name": "Platz Default",
            "available_from": "2026-06-01",
            "available_to": "2026-08-31",
        },
    ).json()
    booking = client.post(
        "/api/v1/bookings",
        json={
            "group_name": "Default Person",
            "start_date": "2026-07-01",
            "end_date": "2026-07-03",
            "pitch_ids": [pitch["id"]],
            "persons": [{"name": "Max", "birth_date": "2000-01-01", "nationality": "AT"}],
        },
    )
    assert booking.status_code == 201, booking.text
    assert booking.json()["persons"][0]["price_profile_id"] == default_id


def test_billing_uses_person_price_profile(client: TestClient):
    default_id = _default_profile_id(client)
    reduced = client.post(
        "/api/v1/price-profiles",
        json={"name": "Ermäßigt", "is_default": False, "sort_order": 1},
    ).json()

    assert (
        client.post(
            "/api/v1/person-fee-elements",
            json={
                "price_profile_id": default_id,
                "name": "Gebühr",
                "kind": "fixed",
                "daily_price": 10,
                "sort_order": 1,
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/person-fee-elements",
            json={
                "price_profile_id": reduced["id"],
                "name": "Gebühr",
                "kind": "fixed",
                "daily_price": 2,
                "sort_order": 1,
            },
        ).status_code
        == 201
    )

    pitch = client.post(
        "/api/v1/pitches",
        json={
            "name": "Platz Zwei Profile",
            "available_from": "2026-06-01",
            "available_to": "2026-08-31",
            "daily_price": 0,
        },
    ).json()
    booking = client.post(
        "/api/v1/bookings",
        json={
            "group_name": "Zwei Tarife",
            "start_date": "2026-07-01",
            "end_date": "2026-07-03",
            "pitch_ids": [pitch["id"]],
            "persons": [
                {
                    "name": "Voll",
                    "birth_date": "2000-01-01",
                    "nationality": "AT",
                    "price_profile_id": default_id,
                },
                {
                    "name": "Ermäßigt",
                    "birth_date": "2000-01-01",
                    "nationality": "AT",
                    "price_profile_id": reduced["id"],
                },
            ],
        },
    )
    assert booking.status_code == 201, booking.text
    inv = client.get(f"/api/v1/bookings/{booking.json()['id']}/invoice").json()
    # 2 nights: 10*2 + 2*2 = 24
    assert inv["total"] == 24.0
    person_amounts = {
        line["label"].split(" ")[0]: line["amount"]
        for line in inv["lines"]
        if line["category"] == "person"
    }
    assert person_amounts["Voll"] == 20.0
    assert person_amounts["Ermäßigt"] == 4.0


def test_fee_elements_scoped_to_profile(client: TestClient):
    default_id = _default_profile_id(client)
    other = client.post(
        "/api/v1/price-profiles",
        json={"name": "Andere", "is_default": False},
    ).json()
    client.post(
        "/api/v1/person-fee-elements",
        json={
            "price_profile_id": default_id,
            "name": "Nur Standard",
            "kind": "fixed",
            "daily_price": 1,
        },
    )
    client.post(
        "/api/v1/person-fee-elements",
        json={
            "price_profile_id": other["id"],
            "name": "Nur Andere",
            "kind": "fixed",
            "daily_price": 2,
        },
    )
    standard_els = client.get(f"/api/v1/person-fee-elements?price_profile_id={default_id}").json()
    other_els = client.get(f"/api/v1/person-fee-elements?price_profile_id={other['id']}").json()
    assert [e["name"] for e in standard_els] == ["Nur Standard"]
    assert [e["name"] for e in other_els] == ["Nur Andere"]
