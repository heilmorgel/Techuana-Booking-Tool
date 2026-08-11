from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from app.services.gaesteblatt import map_nationality, parse_gaesteblatt_bytes

FIXTURE = Path(__file__).parent / "fixtures" / "gaesteblatt_sample.xlsx"
SAMPLE_CANDIDATES = [
    Path(__file__).resolve().parents[3] / "Samples" / "GästeBlatt_2026_ZeltPlatz_Gruppe _.xltx",
    Path(__file__).resolve().parents[2].parent / "Samples" / "GästeBlatt_2026_ZeltPlatz_Gruppe _.xltx",
]


def test_map_nationality_aliases():
    assert map_nationality("Österreich") == "AT"
    assert map_nationality("deutschland") == "DE"
    assert map_nationality("AT") == "AT"
    assert map_nationality("UnbekanntlandXYZ") == "XX"


def test_parse_gaesteblatt_fixture():
    content = FIXTURE.read_bytes()
    draft = parse_gaesteblatt_bytes(content)
    assert draft.group_name == "Pfadfindergruppe Test"
    assert draft.start_date == date(2026, 7, 10)
    assert draft.end_date == date(2026, 7, 15)
    assert "Muster Max" in draft.group_leader
    assert "Hauptstr. 1" in draft.group_leader
    names = [p.name for p in draft.persons]
    assert names[0] == "Muster Max"
    assert "Schmidt Anna" in names
    assert "Weber Tom" in names
    leader = draft.persons[0]
    assert leader.nationality == "DE"
    assert leader.travel_document == "RP A123456"
    weber = next(p for p in draft.persons if p.name == "Weber Tom")
    assert weber.nationality == "DE"
    assert "PA B998877" in weber.travel_document
    schmidt = next(p for p in draft.persons if p.name == "Schmidt Anna")
    assert schmidt.nationality == "AT"
    assert any("Personenliste" in w for w in draft.warnings)


def test_parse_gaesteblatt_api(client: TestClient):
    with FIXTURE.open("rb") as fh:
        res = client.post(
            "/api/v1/bookings/parse-gaesteblatt",
            files={
                "file": (
                    "gaesteblatt_sample.xlsx",
                    fh,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["group_name"] == "Pfadfindergruppe Test"
    assert len(data["persons"]) >= 3


def test_booking_persists_group_leader_and_travel_document(client: TestClient):
    pitch = client.post(
        "/api/v1/pitches",
        json={
            "name": "Platz Gästeblatt",
            "available_from": "2026-06-01",
            "available_to": "2026-09-30",
            "daily_price": 5,
        },
    ).json()
    created = client.post(
        "/api/v1/bookings",
        json={
            "group_name": "Import Gruppe",
            "group_leader": "Max Muster\nHauptstr. 1",
            "start_date": "2026-07-10",
            "end_date": "2026-07-15",
            "pitch_ids": [pitch["id"]],
            "persons": [
                {
                    "name": "Weber Tom",
                    "birth_date": "2008-08-20",
                    "nationality": "DE",
                    "travel_document": "PA B998877",
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["group_leader"].startswith("Max Muster")
    assert body["persons"][0]["travel_document"] == "PA B998877"

    fetched = client.get(f"/api/v1/bookings/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["group_leader"].startswith("Max Muster")


def test_home_country_meta_and_operator_settings(client: TestClient):
    meta = client.get("/api/v1/meta")
    assert meta.status_code == 200
    assert meta.json()["home_country"] == "AT"
    assert any(c["code"] == "AT" for c in meta.json()["countries"])

    patched = client.patch("/api/v1/operator-settings", json={"home_country": "DE"})
    assert patched.status_code == 200, patched.text
    assert patched.json()["home_country"] == "DE"
    assert client.get("/api/v1/meta").json()["home_country"] == "DE"

    bad = client.patch("/api/v1/operator-settings", json={"home_country": "ZZ"})
    assert bad.status_code == 422


def test_parse_real_sample_template_if_present():
    sample = next((p for p in SAMPLE_CANDIDATES if p.is_file()), None)
    if sample is None:
        return
    draft = parse_gaesteblatt_bytes(sample.read_bytes())
    # Empty template: group name may be blank, but sheet must parse
    assert draft.persons == [] or isinstance(draft.persons, list)
    assert draft.group_name is not None
