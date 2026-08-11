from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.services.billing import age_on_date


def _default_profile_id(client: TestClient) -> int:
    profiles = client.get("/api/v1/price-profiles").json()
    return next(p["id"] for p in profiles if p["is_default"])


def test_age_on_arrival_day():
    assert age_on_date(date(2009, 7, 15), date(2026, 7, 14)) == 16
    assert age_on_date(date(2009, 7, 15), date(2026, 7, 15)) == 17


def test_booking_without_persons(client: TestClient):
    pitch = client.post(
        "/api/v1/pitches",
        json={
            "name": "Platz Billing",
            "available_from": "2026-06-01",
            "available_to": "2026-08-31",
            "daily_price": 10,
        },
    )
    assert pitch.status_code == 201, pitch.text
    r = client.post(
        "/api/v1/bookings",
        json={
            "group_name": "Ohne Personen",
            "start_date": "2026-07-01",
            "end_date": "2026-07-04",
            "pitch_ids": [pitch.json()["id"]],
            "persons": [],
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["persons"] == []

    inv = client.get(f"/api/v1/bookings/{r.json()['id']}/invoice")
    assert inv.status_code == 200
    data = inv.json()
    assert data["nights"] == 3
    assert all(line["category"] != "person" for line in data["lines"])
    assert data["total"] == 30.0


def test_zero_price_lines_hidden(client: TestClient):
    pitch = client.post(
        "/api/v1/pitches",
        json={
            "name": "Platz Null",
            "available_from": "2026-06-01",
            "available_to": "2026-08-31",
            "daily_price": 0,
        },
    ).json()
    booking = client.post(
        "/api/v1/bookings",
        json={
            "group_name": "Null",
            "start_date": "2026-07-01",
            "end_date": "2026-07-03",
            "pitch_ids": [pitch["id"]],
            "persons": [],
        },
    ).json()
    inv = client.get(f"/api/v1/bookings/{booking['id']}/invoice").json()
    assert inv["lines"] == []
    assert inv["total"] == 0


def test_age_brackets_and_pdf(client: TestClient):
    profile_id = _default_profile_id(client)
    pitch = client.post(
        "/api/v1/pitches",
        json={
            "name": "Platz Alter",
            "available_from": "2026-06-01",
            "available_to": "2026-08-31",
            "daily_price": 5,
        },
    ).json()
    tax = client.post(
        "/api/v1/person-fee-elements",
        json={
            "price_profile_id": profile_id,
            "name": "Tourismusabgabe",
            "kind": "fixed",
            "daily_price": 1.5,
            "sort_order": 1,
        },
    )
    assert tax.status_code == 201, tax.text
    fee = client.post(
        "/api/v1/person-fee-elements",
        json={
            "price_profile_id": profile_id,
            "name": "Lagerbeitrag",
            "kind": "age_based",
            "sort_order": 2,
            "brackets": [
                {"age_from": 0, "age_to_exclusive": 17, "daily_price": 3},
                {"age_from": 17, "age_to_exclusive": None, "daily_price": 8},
            ],
        },
    )
    assert fee.status_code == 201, fee.text

    # Child 16 on arrival (birthday next day would be 17)
    booking = client.post(
        "/api/v1/bookings",
        json={
            "group_name": "Familie",
            "start_date": "2026-07-14",
            "end_date": "2026-07-16",
            "pitch_ids": [pitch["id"]],
            "persons": [
                {"name": "Kind", "birth_date": "2009-07-15", "nationality": "AT"},
                {"name": "Erwachsen", "birth_date": "2000-01-01", "nationality": "AT"},
            ],
        },
    )
    assert booking.status_code == 201, booking.text
    inv = client.get(f"/api/v1/bookings/{booking.json()['id']}/invoice").json()
    assert inv["nights"] == 2
    # pitch 5*2=10; kind: tax 1.5*2 + lager 3*2 = 9; adult: 1.5*2 + 8*2 = 19; total 38
    assert inv["total"] == 38.0
    labels = " ".join(line["label"] for line in inv["lines"])
    assert "Kind (16 J." in labels
    assert "Erwachsen (26 J." in labels
    assert "2026-07-14" not in labels
    assert all(line.get("start_date") and line.get("end_date") for line in inv["lines"] if line["category"] != "custom")
    assert "Tourismusabgabe" not in labels
    assert "Lagerbeitrag" not in labels
    person_lines = [line for line in inv["lines"] if line["category"] == "person"]
    assert len(person_lines) == 2
    assert {line["amount"] for line in person_lines} == {9.0, 19.0}
    cat_order = {"pitch": 0, "person": 1, "service": 2, "custom": 3}
    categories = [line["category"] for line in inv["lines"]]
    assert categories == sorted(categories, key=lambda c: cat_order[c])

    pdf = client.get(f"/api/v1/bookings/{booking.json()['id']}/invoice.pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content[:4] == b"%PDF"


def test_custom_invoice_lines_positive_negative_and_zero_note(client: TestClient):
    pitch = client.post(
        "/api/v1/pitches",
        json={
            "name": "Platz Custom",
            "available_from": "2026-06-01",
            "available_to": "2026-08-31",
            "daily_price": 10,
        },
    ).json()
    booking = client.post(
        "/api/v1/bookings",
        json={
            "group_name": "Custom Pos",
            "start_date": "2026-07-01",
            "end_date": "2026-07-03",
            "pitch_ids": [pitch["id"]],
            "persons": [],
        },
    ).json()
    bid = booking["id"]

    # Pitch 10 * 2 = 20
    inv0 = client.get(f"/api/v1/bookings/{bid}/invoice").json()
    assert inv0["total"] == 20.0
    assert all(line["category"] != "custom" for line in inv0["lines"])

    surcharge = client.post(
        f"/api/v1/bookings/{bid}/invoice/custom-lines",
        json={"label": "Holzlieferung", "amount": 15.5},
    )
    assert surcharge.status_code == 201, surcharge.text
    discount = client.post(
        f"/api/v1/bookings/{bid}/invoice/custom-lines",
        json={"label": "Treuerabatt", "amount": -5},
    )
    assert discount.status_code == 201, discount.text
    note = client.post(
        f"/api/v1/bookings/{bid}/invoice/custom-lines",
        json={"label": "Hinweis: Barzahlung", "amount": 0},
    )
    assert note.status_code == 201, note.text
    note_id = note.json()["id"]

    inv = client.get(f"/api/v1/bookings/{bid}/invoice").json()
    custom = [line for line in inv["lines"] if line["category"] == "custom"]
    assert len(custom) == 3
    assert {line["label"] for line in custom} == {
        "Holzlieferung",
        "Treuerabatt",
        "Hinweis: Barzahlung",
    }
    assert any(line["amount"] == 0 and line["label"].startswith("Hinweis") for line in custom)
    # 20 + 15.5 - 5 + 0 = 30.5
    assert inv["total"] == 30.5

    # Zero auto-lines still hidden; only custom zero notes appear
    zero_pitch = client.post(
        "/api/v1/pitches",
        json={
            "name": "Platz Custom Null",
            "available_from": "2026-06-01",
            "available_to": "2026-08-31",
            "daily_price": 0,
        },
    ).json()
    booking2 = client.post(
        "/api/v1/bookings",
        json={
            "group_name": "Nur Notiz",
            "start_date": "2026-07-10",
            "end_date": "2026-07-12",
            "pitch_ids": [zero_pitch["id"]],
            "persons": [],
        },
    ).json()
    bid2 = booking2["id"]
    assert (
        client.post(
            f"/api/v1/bookings/{bid2}/invoice/custom-lines",
            json={"label": "Nur Notiz-Position", "amount": 0},
        ).status_code
        == 201
    )
    inv2 = client.get(f"/api/v1/bookings/{bid2}/invoice").json()
    assert len(inv2["lines"]) == 1
    assert inv2["lines"][0]["category"] == "custom"
    assert inv2["lines"][0]["amount"] == 0
    assert inv2["total"] == 0

    deleted = client.delete(f"/api/v1/bookings/{bid}/invoice/custom-lines/{note_id}")
    assert deleted.status_code == 204
    inv3 = client.get(f"/api/v1/bookings/{bid}/invoice").json()
    assert not any(line["label"].startswith("Hinweis") for line in inv3["lines"])
    assert inv3["total"] == 30.5  # note was 0

    pdf = client.get(f"/api/v1/bookings/{bid}/invoice.pdf")
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"


def test_smoke_custom_invoice_line_on_billing(client: TestClient):
    """Smoke: custom line via Abrechnung API affects total and PDF."""
    pitch = client.post(
        "/api/v1/pitches",
        json={
            "name": "Smoke Custom Platz",
            "available_from": "2026-06-01",
            "available_to": "2026-08-31",
            "daily_price": 20,
        },
    ).json()
    booking = client.post(
        "/api/v1/bookings",
        json={
            "group_name": "Smoke Custom",
            "start_date": "2026-08-01",
            "end_date": "2026-08-03",
            "pitch_ids": [pitch["id"]],
            "persons": [],
        },
    ).json()
    bid = booking["id"]

    created = client.post(
        f"/api/v1/bookings/{bid}/invoice/custom-lines",
        json={"label": "Kaution einbehalten", "amount": -10},
    )
    assert created.status_code == 201, created.text
    line_id = created.json()["id"]

    billing = client.get("/api/v1/billing?from_date=2026-01-01&to_date=2026-12-31")
    assert billing.status_code == 200
    row = next(item for item in billing.json() if item["booking_id"] == bid)
    assert row["total"] == 30.0  # 20*2 - 10

    inv = client.get(f"/api/v1/bookings/{bid}/invoice").json()
    assert inv["total"] == 30.0
    assert any(l["id"] == line_id and l["amount"] == -10 for l in inv["lines"])

    patched = client.patch(
        f"/api/v1/bookings/{bid}/invoice/custom-lines/{line_id}",
        json={"label": "Kaution (korrigiert)", "amount": -5},
    )
    assert patched.status_code == 200, patched.text
    inv2 = client.get(f"/api/v1/bookings/{bid}/invoice").json()
    assert inv2["total"] == 35.0

    pdf = client.get(f"/api/v1/bookings/{bid}/invoice.pdf")
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"


def test_person_custom_dates_affect_billing(client: TestClient):
    profile_id = _default_profile_id(client)
    pitch = client.post(
        "/api/v1/pitches",
        json={
            "name": "Platz PersonDates",
            "available_from": "2026-06-01",
            "available_to": "2026-08-31",
            "daily_price": 0,
        },
    ).json()
    assert (
        client.post(
            "/api/v1/person-fee-elements",
            json={
                "price_profile_id": profile_id,
                "name": "Tagesgebühr",
                "kind": "fixed",
                "daily_price": 10,
                "sort_order": 1,
            },
        ).status_code
        == 201
    )
    booking = client.post(
        "/api/v1/bookings",
        json={
            "group_name": "Teilzeit",
            "start_date": "2026-07-01",
            "end_date": "2026-07-05",
            "pitch_ids": [pitch["id"]],
            "persons": [
                {
                    "name": "Kurz",
                    "birth_date": "2000-01-01",
                    "nationality": "AT",
                    "start_date": "2026-07-02",
                    "end_date": "2026-07-04",
                },
                {
                    "name": "Voll",
                    "birth_date": "2000-01-01",
                    "nationality": "AT",
                },
            ],
        },
    )
    assert booking.status_code == 201, booking.text
    persons = booking.json()["persons"]
    assert persons[0]["start_date"] == "2026-07-02"
    assert persons[0]["end_date"] == "2026-07-04"
    assert persons[1]["start_date"] == "2026-07-01"
    assert persons[1]["end_date"] == "2026-07-05"

    inv = client.get(f"/api/v1/bookings/{booking.json()['id']}/invoice").json()
    # Kurz 2 Nächte × 10 + Voll 4 Nächte × 10 = 60
    assert inv["total"] == 60.0


def test_person_dates_outside_booking_rejected(client: TestClient):
    pitch = client.post(
        "/api/v1/pitches",
        json={
            "name": "Platz Range",
            "available_from": "2026-06-01",
            "available_to": "2026-08-31",
        },
    ).json()
    r = client.post(
        "/api/v1/bookings",
        json={
            "group_name": "Falsch",
            "start_date": "2026-07-01",
            "end_date": "2026-07-05",
            "pitch_ids": [pitch["id"]],
            "persons": [
                {
                    "name": "Zu früh",
                    "birth_date": "2000-01-01",
                    "nationality": "AT",
                    "start_date": "2026-06-30",
                    "end_date": "2026-07-03",
                }
            ],
        },
    )
    assert r.status_code == 422


def test_smoke_admin_prices_booking_billing_pdf(client: TestClient):
    """End-to-end smoke: Preise setzen → buchen → Abrechnung → PDF."""
    profile_id = _default_profile_id(client)
    pitch = client.post(
        "/api/v1/pitches",
        json={
            "name": "Smoke Platz",
            "available_from": "2026-06-01",
            "available_to": "2026-08-31",
            "daily_price": 12.5,
        },
    )
    assert pitch.status_code == 201, pitch.text
    assert (
        client.post(
            "/api/v1/person-fee-elements",
            json={
                "price_profile_id": profile_id,
                "name": "Tourismusabgabe",
                "kind": "fixed",
                "daily_price": 1.5,
                "sort_order": 1,
            },
        ).status_code
        == 201
    )
    booking = client.post(
        "/api/v1/bookings",
        json={
            "group_name": "Smoke Gruppe",
            "start_date": "2026-07-10",
            "end_date": "2026-07-12",
            "pitch_ids": [pitch.json()["id"]],
            "persons": [{"name": "Max", "birth_date": "2000-01-01", "nationality": "AT"}],
        },
    )
    assert booking.status_code == 201, booking.text
    bid = booking.json()["id"]

    billing = client.get("/api/v1/billing?from_date=2026-01-01&to_date=2026-12-31")
    assert billing.status_code == 200
    assert any(item["booking_id"] == bid for item in billing.json())

    inv = client.get(f"/api/v1/bookings/{bid}/invoice")
    assert inv.status_code == 200
    data = inv.json()
    assert data["total"] > 0
    assert data["invoice_number"]
    assert "-" in data["invoice_number"]
    assert all(line["amount"] > 0 for line in data["lines"])
    person_lines = [line for line in data["lines"] if line["category"] == "person"]
    assert len(person_lines) == 1
    assert person_lines[0]["label"].startswith("Max (")
    assert "Tourismusabgabe" not in person_lines[0]["label"]

    pdf = client.get(f"/api/v1/bookings/{bid}/invoice.pdf")
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"
    assert f'rechnung-{data["invoice_number"]}.pdf' in pdf.headers.get("content-disposition", "")


def test_invoice_number_assigned_once_and_sequential(client: TestClient, monkeypatch):
    from datetime import date as date_cls

    from app.services import invoice_number as inv_mod

    monkeypatch.setattr(inv_mod, "date", type("D", (), {"today": staticmethod(lambda: date_cls(2026, 8, 11))}))

    pitch = client.post(
        "/api/v1/pitches",
        json={
            "name": "Platz RN",
            "available_from": "2026-06-01",
            "available_to": "2026-08-31",
            "daily_price": 5,
        },
    ).json()

    def _book(name: str, start: str, end: str) -> int:
        r = client.post(
            "/api/v1/bookings",
            json={
                "group_name": name,
                "start_date": start,
                "end_date": end,
                "pitch_ids": [pitch["id"]],
                "persons": [],
            },
        )
        assert r.status_code == 201, r.text
        return r.json()["id"]

    bid1 = _book("Gruppe A", "2026-07-01", "2026-07-03")
    bid2 = _book("Gruppe B", "2026-07-05", "2026-07-07")

    billing = client.get("/api/v1/billing").json()
    row1 = next(item for item in billing if item["booking_id"] == bid1)
    assert row1["invoice_number"] is None

    inv1 = client.get(f"/api/v1/bookings/{bid1}/invoice").json()
    assert inv1["invoice_number"] == "20260811-0001"
    inv1_again = client.get(f"/api/v1/bookings/{bid1}/invoice").json()
    assert inv1_again["invoice_number"] == "20260811-0001"

    inv2 = client.get(f"/api/v1/bookings/{bid2}/invoice").json()
    assert inv2["invoice_number"] == "20260811-0002"
    assert inv2["invoice_number"] != inv1["invoice_number"]

    pdf = client.get(f"/api/v1/bookings/{bid1}/invoice.pdf")
    assert pdf.status_code == 200
    assert 'filename="rechnung-20260811-0001.pdf"' in pdf.headers.get("content-disposition", "")

    billing2 = client.get("/api/v1/billing").json()
    assert next(item for item in billing2 if item["booking_id"] == bid1)["invoice_number"] == "20260811-0001"
    assert next(item for item in billing2 if item["booking_id"] == bid2)["invoice_number"] == "20260811-0002"
