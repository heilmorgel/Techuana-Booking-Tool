from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image


def _tiny_png() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (32, 32), color=(47, 93, 58)).save(buf, format="PNG")
    return buf.getvalue()


def test_operator_settings_crud_and_logo(client: TestClient):
    empty = client.get("/api/v1/operator-settings")
    assert empty.status_code == 200
    assert empty.json()["organization_name"] == ""
    assert empty.json()["has_logo"] is False

    updated = client.patch(
        "/api/v1/operator-settings",
        json={
            "organization_name": "Pfadfinder Musterstadt",
            "address": "Lagerweg 1\n1234 Musterstadt",
            "iban": "at61 1904 3002 3457 3201",
        },
    )
    assert updated.status_code == 200, updated.text
    data = updated.json()
    assert data["organization_name"] == "Pfadfinder Musterstadt"
    assert "Lagerweg 1" in data["address"]
    assert data["iban"] == "AT611904300234573201"

    upload = client.post(
        "/api/v1/operator-settings/logo",
        files={"file": ("logo.png", _tiny_png(), "image/png")},
    )
    assert upload.status_code == 200, upload.text
    assert upload.json()["has_logo"] is True

    logo = client.get("/api/v1/operator-settings/logo")
    assert logo.status_code == 200
    assert logo.headers["content-type"].startswith("image/")
    assert logo.content[:8] == b"\x89PNG\r\n\x1a\n"

    removed = client.delete("/api/v1/operator-settings/logo")
    assert removed.status_code == 200
    assert removed.json()["has_logo"] is False
    assert client.get("/api/v1/operator-settings/logo").status_code == 404


def test_invoice_includes_operator_header_footer(client: TestClient):
    client.patch(
        "/api/v1/operator-settings",
        json={
            "organization_name": "Verein Alpen",
            "address": "Bergstr. 9\n5020 Salzburg",
            "iban": "AT123456789012345678",
        },
    )
    client.post(
        "/api/v1/operator-settings/logo",
        files={"file": ("club.png", _tiny_png(), "image/png")},
    )

    pitch = client.post(
        "/api/v1/pitches",
        json={
            "name": "Platz Betreiber",
            "available_from": "2026-06-01",
            "available_to": "2026-08-31",
            "daily_price": 10,
        },
    ).json()
    booking = client.post(
        "/api/v1/bookings",
        json={
            "group_name": "Testgruppe",
            "start_date": "2026-07-01",
            "end_date": "2026-07-03",
            "pitch_ids": [pitch["id"]],
            "persons": [],
        },
    ).json()

    inv = client.get(f"/api/v1/bookings/{booking['id']}/invoice").json()
    assert inv["operator"]["organization_name"] == "Verein Alpen"
    assert "Salzburg" in inv["operator"]["address"]
    assert inv["operator"]["iban"] == "AT123456789012345678"
    assert inv["operator"]["has_logo"] is True

    pdf = client.get(f"/api/v1/bookings/{booking['id']}/invoice.pdf")
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"
    assert len(pdf.content) > 1500


def test_smoke_operator_settings_on_invoice(client: TestClient):
    """Smoke: Betreiberdaten speichern → Rechnung enthält Kopf/Fuß."""
    assert (
        client.patch(
            "/api/v1/operator-settings",
            json={
                "organization_name": "Smoke Verein",
                "address": "Testgasse 1\n1010 Wien",
                "iban": "AT990000000000000001",
            },
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/operator-settings/logo",
            files={"file": ("s.png", _tiny_png(), "image/png")},
        ).status_code
        == 200
    )
    pitch = client.post(
        "/api/v1/pitches",
        json={
            "name": "Smoke Betreiber Platz",
            "available_from": "2026-06-01",
            "available_to": "2026-08-31",
            "daily_price": 5,
        },
    )
    assert pitch.status_code == 201
    booking = client.post(
        "/api/v1/bookings",
        json={
            "group_name": "Smoke Ops",
            "start_date": "2026-07-20",
            "end_date": "2026-07-22",
            "pitch_ids": [pitch.json()["id"]],
            "persons": [],
        },
    )
    assert booking.status_code == 201
    inv = client.get(f"/api/v1/bookings/{booking.json()['id']}/invoice")
    assert inv.status_code == 200
    op = inv.json()["operator"]
    assert op["organization_name"] == "Smoke Verein"
    assert op["has_logo"] is True
    assert op["iban"].startswith("AT99")
    assert client.get(f"/api/v1/bookings/{booking.json()['id']}/invoice.pdf").status_code == 200
