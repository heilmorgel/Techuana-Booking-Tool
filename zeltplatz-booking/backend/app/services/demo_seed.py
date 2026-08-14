"""Demo master data (from Samples/DemoData.xlsx) and DB reset helpers."""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base, SessionLocal, engine, init_db
from app.models import Pitch, Service, ServiceGroup
from app.services.operator_settings import ALLOWED_LOGO_EXTENSIONS, data_dir

# (name, daily_price, deposit, available_from, available_to)
DEMO_PITCHES: list[tuple[str, float, float, date, date]] = [
    ('Ahornplatz', 0, 0, date(2026, 6, 1), date(2026, 9, 30)),
    ('Birkenplatz', 0, 0, date(2026, 6, 1), date(2026, 10, 1)),
    ('Castenalplatz', 0, 0, date(2026, 6, 1), date(2026, 10, 2)),
    ('Drachenbaumplatz', 0, 0, date(2026, 6, 1), date(2026, 10, 3)),
    ('Eschenplatz', 0, 0, date(2026, 6, 1), date(2026, 10, 4)),
    ('Fichtenplatz', 0, 0, date(2026, 6, 1), date(2026, 10, 5)),
    ('Ginkoplatz', 0, 0, date(2026, 6, 1), date(2026, 10, 6)),
    ('Haselplatz', 0, 0, date(2026, 6, 1), date(2026, 10, 7)),
    ('Brunnstubenplatz', 0, 0, date(2026, 6, 1), date(2026, 10, 8)),
    ('Lärchenplatz', 0, 0, date(2026, 6, 1), date(2026, 10, 9)),
    ('Steirerplatz', 0, 0, date(2026, 6, 1), date(2026, 10, 10)),
    ('Kärntnerplatz', 0, 0, date(2026, 6, 1), date(2026, 10, 11)),
    ('Leitlplatz', 0, 0, date(2026, 6, 1), date(2026, 10, 12)),
    ('Knappenhaus - Zimmer 1', 20, 0, date(2026, 6, 1), date(2026, 10, 13)),
    ('Knappenhaus - Zimmer 2', 20, 0, date(2026, 6, 1), date(2026, 10, 14)),
    ('Knappenhaus - Dachboden', 20, 0, date(2026, 6, 1), date(2026, 10, 15)),
    ('Blockhaus', 0, 0, date(2026, 6, 1), date(2026, 10, 16)),
    ('Lexehaus', 18, 0, date(2026, 6, 1), date(2026, 10, 17)),
]

# (group, name, available_quantity, daily_price, deposit)
DEMO_SERVICES: list[tuple[str, str, int, float, float]] = [
    ('WC Neu', 'WC Neu - Boys 1', 1, 9.4, 0),
    ('WC Neu', 'WC Neu - Boys 2', 1, 9.4, 0),
    ('WC Neu', 'WC Neu - Boys 3', 1, 9.4, 0),
    ('WC Neu', 'WC Neu - Boys 4', 1, 9.4, 0),
    ('WC Neu', 'WC Neu - Boys 5', 1, 9.4, 0),
    ('WC Neu', 'WC Neu - Boys 6', 1, 9.4, 0),
    ('WC Neu', 'WC Neu - Girls 1', 1, 9.4, 0),
    ('WC Neu', 'WC Neu - Girls 2', 1, 9.4, 0),
    ('WC Neu', 'WC Neu - Girls 3', 1, 9.4, 0),
    ('WC Neu', 'WC Neu - Girls 4', 1, 9.4, 0),
    ('WC Neu', 'WC Neu - Girls 5', 1, 9.4, 0),
    ('WC Neu', 'WC Neu - Girls 6', 1, 9.4, 0),
    ('WC Neu', 'WC Neu - Girls 7', 1, 9.4, 0),
    ('WC Alt', 'WC Alt 1', 1, 9.4, 0),
    ('WC Alt', 'WC Alt 2', 1, 9.4, 0),
    ('WC Alt', 'WC Alt 3', 1, 9.4, 0),
    ('WC Alt', 'WC Alt 4', 1, 9.4, 0),
    ('WC Alt', 'WC Alt 5', 1, 9.4, 0),
    ('WC Alt', 'WC Alt 6', 1, 9.4, 0),
    ('WC Alt', 'WC Alt 11', 1, 9.4, 0),
    ('WC Alt', 'WC Alt 12', 1, 9.4, 0),
    ('WC Alt', 'WC Alt 13', 1, 9.4, 0),
    ('WC Alt', 'WC Alt 14', 1, 9.4, 0),
    ('WC Alt', 'WC Alt 15', 1, 9.4, 0),
    ('WC Alt', 'WC Alt 16', 1, 9.4, 0),
    ('WC Alt', 'WC Alt 17', 1, 9.4, 0),
    ('WC Alt', 'WC Alt 18', 1, 9.4, 0),
    ('WC Alt', 'WC Alt 19', 1, 9.4, 0),
    ('WC Alt', 'WC Alt 20', 1, 9.4, 0),
    ('WC Lexehaus', 'WC Lexe Boys', 1, 9.4, 0),
    ('WC Lexehaus', 'WC Lexe Girls', 1, 9.4, 0),
    ('Knappenhaus - Duschen/Waschen', 'Knappenhaus - Dusche 1', 1, 9.4, 0),
    ('Knappenhaus - Duschen/Waschen', 'Knappenhaus - Dusche 2', 1, 9.4, 0),
    ('Knappenhaus - Duschen/Waschen', 'Knappenhaus - Dusche 3', 1, 9.4, 0),
    ('Knappenhaus - Duschen/Waschen', 'Knappenhaus - Waschraum 1', 1, 9.4, 0),
    ('Knappenhaus - Duschen/Waschen', 'Knappenhaus - Waschraum 2', 1, 9.4, 0),
    ('Küchen', 'Küche Knappenhaus', 1, 25, 0),
    ('Küchen', 'Küche Lexehaus', 1, 25, 0),
    ('Kühlschrank', 'Kühlschrank 1', 1, 4, 0),
    ('Kühlschrank', 'Kühlschrank 2', 1, 4, 0),
    ('Kühlschrank', 'Kühlschrank 3', 1, 4, 0),
    ('Kühlschrank', 'Kühlschrank 4', 1, 4, 0),
    ('Kühlschrank', 'Kühlschrank 5', 1, 4, 0),
    ('Kühlschrank', 'Kühlschrank 6', 1, 4, 0),
    ('Kühlschrank', 'Kühlschrank 7', 1, 4, 0),
    ('Kühlschrank', 'Kühlschrank 8', 1, 4, 0),
    ('Kühlschrank', 'Kühlschrank 9', 1, 4, 0),
    ('Kühlschrank', 'Kühlschrank 10', 1, 4, 0),
    ('Kühlschrank', 'Kühlschrank 11', 1, 4, 0),
    ('Kühlschrank', 'Kühlschrank 12', 1, 4, 0),
    ('Festbankgarnituren', 'Festbankgarnituren', 50, 2, 0),
    ('Handyladebox', 'Ladebox 01', 1, 2, 0),
    ('Handyladebox', 'Ladebox 02', 1, 2, 0),
    ('Handyladebox', 'Ladebox 03', 1, 2, 0),
    ('Handyladebox', 'Ladebox 04', 1, 2, 0),
    ('Handyladebox', 'Ladebox 05', 1, 2, 0),
    ('Handyladebox', 'Ladebox 06', 1, 2, 0),
    ('Handyladebox', 'Ladebox 07', 1, 2, 0),
    ('Handyladebox', 'Ladebox 08', 1, 2, 0),
    ('Handyladebox', 'Ladebox 09', 1, 2, 0),
    ('Handyladebox', 'Ladebox 10', 1, 2, 0),
    ('Handyladebox', 'Ladebox 11', 1, 2, 0),
    ('Handyladebox', 'Ladebox 12', 1, 2, 0),
    ('Handyladebox', 'Ladebox 13', 1, 2, 0),
    ('Handyladebox', 'Ladebox 14', 1, 2, 0),
    ('Handyladebox', 'Ladebox 15', 1, 2, 0),
    ('Handyladebox', 'Ladebox 16', 1, 2, 0),
    ('Handyladebox', 'Ladebox 17', 1, 2, 0),
    ('Handyladebox', 'Ladebox 18', 1, 2, 0),
    ('Handyladebox', 'Ladebox 19', 1, 2, 0),
    ('Handyladebox', 'Ladebox 20', 1, 2, 0),
    ('Parkplatz', 'Parkplatz Tagesgebühr', 15, 4.5, 0),
    ('Parkplatz', 'Wohnwagen Tagesgebühr', 5, 20, 0),
]


def _clear_logo_files() -> None:
    folder = data_dir()
    for ext in ALLOWED_LOGO_EXTENSIONS:
        path = folder / f"operator_logo{ext}"
        if path.is_file():
            path.unlink()


def reset_db() -> None:
    from app import models as _models  # noqa: F401

    get_settings.cache_clear()
    engine.dispose()
    Base.metadata.drop_all(bind=engine)
    init_db()
    _clear_logo_files()


def seed(db: Session | None = None) -> dict[str, int]:
    own_session = db is None
    if db is None:
        db = SessionLocal()
    try:
        pitches = [
            Pitch(
                name=name,
                daily_price=daily_price,
                deposit=deposit,
                available_from=available_from,
                available_to=available_to,
            )
            for name, daily_price, deposit, available_from, available_to in DEMO_PITCHES
        ]
        db.add_all(pitches)

        groups: dict[str, ServiceGroup] = {}
        services: list[Service] = []
        for group_name, name, quantity, daily_price, deposit in DEMO_SERVICES:
            group = groups.get(group_name)
            if group is None:
                group = ServiceGroup(name=group_name)
                db.add(group)
                db.flush()
                groups[group_name] = group
            services.append(
                Service(
                    name=name,
                    group_id=group.id,
                    available_quantity=quantity,
                    daily_price=daily_price,
                    deposit=deposit,
                )
            )
        db.add_all(services)
        db.flush()

        counts = {
            "pitches": len(pitches),
            "service_groups": len(groups),
            "services": len(services),
            "bookings": 0,
        }
        if own_session:
            db.commit()
        return counts
    except Exception:
        if own_session:
            db.rollback()
        raise
    finally:
        if own_session:
            db.close()


def reset_and_seed() -> dict[str, int]:
    reset_db()
    return seed()
