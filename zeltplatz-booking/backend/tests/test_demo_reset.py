from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.services.demo_seed import DEMO_PITCHES, DEMO_SERVICES


def _tiny_png() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (32, 32), color=(47, 93, 58)).save(buf, format="PNG")
    return buf.getvalue()


def test_demo_reset_replaces_data(client: TestClient):
    extra = client.post(
        "/api/v1/pitches",
        json={
            "name": "TEMP-RESET",
            "available_from": "2026-06-01",
            "available_to": "2026-09-30",
            "daily_price": 99,
        },
    )
    assert extra.status_code == 201, extra.text

    client.patch(
        "/api/v1/operator-settings",
        json={"organization_name": "Wird gelöscht"},
    )
    upload = client.post(
        "/api/v1/operator-settings/logo",
        files={"file": ("logo.png", _tiny_png(), "image/png")},
    )
    assert upload.status_code == 200, upload.text
    assert upload.json()["has_logo"] is True

    reset = client.post("/api/v1/demo/reset")
    assert reset.status_code == 200, reset.text
    body = reset.json()
    assert body["pitches"] == len(DEMO_PITCHES)
    assert body["services"] == len(DEMO_SERVICES)
    assert body["service_groups"] == len({row[0] for row in DEMO_SERVICES})
    assert body["bookings"] == 0

    pitches = client.get("/api/v1/pitches").json()
    names = {p["name"] for p in pitches}
    assert "TEMP-RESET" not in names
    assert "Ahornplatz" in names
    assert "Lexehaus" in names
    assert "Nordwiese" not in names
    assert len(pitches) == len(DEMO_PITCHES)

    lexehaus = next(p for p in pitches if p["name"] == "Lexehaus")
    assert float(lexehaus["daily_price"]) == 18
    assert lexehaus["available_from"] == "2026-06-01"
    assert lexehaus["available_to"] == "2026-10-17"

    services = client.get("/api/v1/services").json()
    assert len(services) == len(DEMO_SERVICES)
    assert any(s["name"] == "Küche Knappenhaus" for s in services)
    assert any(s["name"] == "Parkplatz Tagesgebühr" for s in services)

    groups = client.get("/api/v1/service-groups").json()
    assert len(groups) == body["service_groups"]

    bookings = client.get("/api/v1/bookings").json()
    assert bookings == []

    operator = client.get("/api/v1/operator-settings").json()
    assert operator["organization_name"] == ""
    assert operator["has_logo"] is False
    assert client.get("/api/v1/operator-settings/logo").status_code == 404


def test_demo_reset_get_not_allowed(client: TestClient):
    assert client.get("/api/v1/demo/reset").status_code == 405
