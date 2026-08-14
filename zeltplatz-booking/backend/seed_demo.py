"""Reset local SQLite DB and seed demo data.

Usage (from backend/):
  .\\.venv\\Scripts\\python.exe seed_demo.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _ensure_data_dir() -> Path:
    if os.environ.get("DATA_DIR"):
        data = Path(os.environ["DATA_DIR"])
    else:
        data = ROOT.parent / ".data"
        os.environ["DATA_DIR"] = str(data)
    data.mkdir(parents=True, exist_ok=True)
    return data


def reset_db() -> None:
    from app.services.demo_seed import reset_db as _reset_db

    _reset_db()


def seed() -> dict[str, int]:
    from app.services.demo_seed import seed as _seed

    return _seed()


if __name__ == "__main__":
    data = _ensure_data_dir()
    os.environ.setdefault("DEV_MODE", "1")
    os.environ.setdefault("TZ", "Europe/Vienna")
    reset_db()
    counts = seed()
    print(f"DB zurückgesetzt und befüllt: {data / 'booking.db'}")
    print(f"  Plätze: {counts['pitches']}")
    print(f"  Dienste: {counts['services']} in {counts['service_groups']} Gruppen")
    print(f"  Buchungen: {counts['bookings']}")
