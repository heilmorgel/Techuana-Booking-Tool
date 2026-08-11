"""Reset local SQLite DB and seed demo data.

Usage (from backend/):
  .\\.venv\\Scripts\\python.exe seed_demo.py
"""
from __future__ import annotations

import os
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent / ".data"
DATA.mkdir(parents=True, exist_ok=True)

os.environ["DATA_DIR"] = str(DATA)
os.environ["DEV_MODE"] = "1"
os.environ.setdefault("TZ", "Europe/Vienna")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.database import Base, SessionLocal, engine, init_db
from app.models import (
    Booking,
    BookingPitch,
    BookingService,
    Person,
    PersonFeeBracket,
    PersonFeeElement,
    Pitch,
    Service,
    ServiceGroup,
)


def reset_db() -> None:
    get_settings.cache_clear()
    Base.metadata.drop_all(bind=engine)
    init_db()


def seed() -> None:
    today = date.today()
    season_from = date(today.year, 5, 1)
    season_to = date(today.year, 9, 30)

    db = SessionLocal()
    try:
        pitches = [
            Pitch(
                name="Nordwiese",
                available_from=season_from,
                available_to=season_to,
                daily_price=25,
            ),
            Pitch(
                name="Südwiese",
                available_from=season_from,
                available_to=season_to,
                daily_price=22,
            ),
            Pitch(
                name="Waldrand",
                available_from=season_from,
                available_to=season_to,
                daily_price=18,
            ),
            Pitch(
                name="Bachplatz",
                available_from=season_from,
                available_to=season_to,
                daily_price=20,
            ),
            Pitch(
                name="Feuerstelle Ost",
                available_from=season_from,
                available_to=season_to,
                daily_price=15,
            ),
        ]
        db.add_all(pitches)
        db.flush()

        g_infra = ServiceGroup(name="Infrastruktur")
        g_material = ServiceGroup(name="Material")
        db.add_all([g_infra, g_material])
        db.flush()

        services = [
            Service(name="Stromanschluss", group_id=g_infra.id, available_quantity=4, daily_price=5),
            Service(name="Wasseranschluss", group_id=g_infra.id, available_quantity=3, daily_price=3),
            Service(name="Kühlschrank", group_id=g_material.id, available_quantity=2, daily_price=4),
            Service(name="Holzbänke", group_id=g_material.id, available_quantity=10, daily_price=1),
            Service(name="Pavillon", group_id=g_material.id, available_quantity=1, daily_price=8),
        ]
        db.add_all(services)
        db.flush()

        tax = PersonFeeElement(
            name="Tourismusabgabe",
            kind="fixed",
            daily_price=1.5,
            sort_order=1,
        )
        lager = PersonFeeElement(
            name="Lagerbeitrag",
            kind="age_based",
            daily_price=0,
            sort_order=2,
        )
        db.add_all([tax, lager])
        db.flush()
        db.add_all(
            [
                PersonFeeBracket(element_id=lager.id, age_from=0, age_to_exclusive=17, daily_price=3),
                PersonFeeBracket(element_id=lager.id, age_from=17, age_to_exclusive=None, daily_price=8),
            ]
        )

        # Past booking
        past_start = today - timedelta(days=20)
        past_end = today - timedelta(days=15)
        past = Booking(
            group_name="Stamm Adler (Vergangenheit)",
            start_date=past_start,
            end_date=past_end,
            notes="Bereits abgerechnet",
        )
        past.booking_pitches = [
            BookingPitch(pitch_id=pitches[0].id, start_date=past_start, end_date=past_end),
        ]
        past.persons = [
            Person(
                name="Anna Adler",
                birth_date=date(2005, 3, 12),
                nationality="AT",
                start_date=past_start,
                end_date=past_end,
            ),
            Person(
                name="Ben Berger",
                birth_date=date(2012, 7, 1),
                nationality="AT",
                start_date=past_start,
                end_date=past_end,
            ),
        ]
        past.booking_services = [
            BookingService(
                service_id=services[0].id,
                quantity=1,
                start_date=past_start,
                end_date=past_end,
            ),
        ]
        db.add(past)

        # Running booking (started before today, ends after today)
        run_start = today - timedelta(days=2)
        run_end = today + timedelta(days=5)
        running = Booking(
            group_name="Pfadfindergruppe Alpen",
            start_date=run_start,
            end_date=run_end,
            notes="Laufendes Lager — Anpassen testen",
        )
        running.booking_pitches = [
            BookingPitch(pitch_id=pitches[1].id, start_date=run_start, end_date=run_end),
            BookingPitch(pitch_id=pitches[2].id, start_date=run_start, end_date=run_end),
        ]
        running.persons = [
            Person(
                name="Max Muster",
                birth_date=date(2000, 1, 15),
                nationality="AT",
                start_date=run_start,
                end_date=run_end,
            ),
            Person(
                name="Eva Beispiel",
                birth_date=date(2011, 6, 20),
                nationality="DE",
                start_date=run_start,
                end_date=run_end,
            ),
            Person(
                name="Leo Kurz",
                birth_date=date(2008, 11, 2),
                nationality="AT",
                start_date=run_start + timedelta(days=1),
                end_date=run_end - timedelta(days=1),
            ),
        ]
        running.booking_services = [
            BookingService(
                service_id=services[0].id,
                quantity=1,
                start_date=run_start,
                end_date=run_end,
            ),
            BookingService(
                service_id=services[2].id,
                quantity=1,
                start_date=run_start,
                end_date=run_end,
            ),
            BookingService(
                service_id=services[3].id,
                quantity=4,
                start_date=run_start,
                end_date=run_end,
            ),
        ]
        db.add(running)

        # Future booking
        fut_start = today + timedelta(days=10)
        fut_end = today + timedelta(days=14)
        future = Booking(
            group_name="Stamm Fuchs",
            start_date=fut_start,
            end_date=fut_end,
            notes="",
        )
        future.booking_pitches = [
            BookingPitch(pitch_id=pitches[3].id, start_date=fut_start, end_date=fut_end),
            BookingPitch(pitch_id=pitches[4].id, start_date=fut_start, end_date=fut_end),
        ]
        future.persons = [
            Person(
                name="Clara Camp",
                birth_date=date(2003, 9, 9),
                nationality="AT",
                start_date=fut_start,
                end_date=fut_end,
            ),
        ]
        future.booking_services = [
            BookingService(
                service_id=services[4].id,
                quantity=1,
                start_date=fut_start,
                end_date=fut_end,
            ),
            BookingService(
                service_id=services[1].id,
                quantity=1,
                start_date=fut_start,
                end_date=fut_end,
            ),
        ]
        db.add(future)

        # Arrival today (fully editable)
        arr_start = today
        arr_end = today + timedelta(days=3)
        arriving = Booking(
            group_name="Gruppe Anreise Heute",
            start_date=arr_start,
            end_date=arr_end,
            notes="Anreisetag — volle Bearbeitung möglich",
        )
        arriving.booking_pitches = [
            BookingPitch(pitch_id=pitches[0].id, start_date=arr_start, end_date=arr_end),
        ]
        arriving.persons = []
        arriving.booking_services = []
        db.add(arriving)

        db.commit()
        print(f"DB zurückgesetzt und befüllt: {DATA / 'booking.db'}")
        print(f"  Plätze: {len(pitches)}")
        print(f"  Dienste: {len(services)} in 2 Gruppen")
        print("  Personenpreise: Tourismusabgabe + Lagerbeitrag")
        print("  Buchungen: 4 (Vergangenheit, laufend, Zukunft, Anreise heute)")
    finally:
        db.close()


if __name__ == "__main__":
    reset_db()
    seed()
