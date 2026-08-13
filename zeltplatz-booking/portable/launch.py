"""Start the portable Zeltplatz Buchung test server."""
from __future__ import annotations

import os
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "app" / "backend"
DATA = ROOT / "data"
HOST = "127.0.0.1"
PORT = 8000
PID_FILE = DATA / "server.pid"


def setup_env() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    os.environ["DATA_DIR"] = str(DATA)
    os.environ["DEV_MODE"] = "1"
    os.environ.setdefault("TZ", "Europe/Vienna")
    os.environ["PYTHONPATH"] = str(BACKEND)
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))


def seed_if_needed() -> None:
    if (DATA / "booking.db").exists():
        return
    print("Lege Demodaten an …")
    import seed_demo

    seed_demo.reset_db()
    seed_demo.seed()


def open_browser_when_ready() -> None:
    health = f"http://{HOST}:{PORT}/api/health"
    for _ in range(50):
        try:
            with urllib.request.urlopen(health, timeout=0.5) as resp:
                if resp.status == 200:
                    webbrowser.open(f"http://{HOST}:{PORT}/")
                    return
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.2)


def main() -> int:
    setup_env()
    dist = ROOT / "app" / "frontend" / "dist"
    if not dist.is_dir():
        print("FEHLER: Frontend fehlt (app\\frontend\\dist).")
        print("Bitte das Testsystem neu aus dem ZIP entpacken.")
        return 1

    try:
        seed_if_needed()
    except Exception as exc:  # noqa: BLE001
        print(f"FEHLER beim Anlegen der Demodaten: {exc}")
        return 1

    PID_FILE.write_text(str(os.getpid()), encoding="ascii")
    print()
    print("Zeltplatz Buchung — Testsystem")
    print(f"  Buchung:      http://{HOST}:{PORT}/")
    print(f"  Verwaltung:   http://{HOST}:{PORT}/admin/")
    print()
    print("Dieses Fenster offen lassen. Schließen beendet das Testsystem.")
    print()

    threading.Thread(target=open_browser_when_ready, daemon=True).start()
    try:
        import uvicorn

        uvicorn.run(
            "app.main:app",
            host=HOST,
            port=PORT,
            reload=False,
            log_level="info",
        )
    except OSError as exc:
        print()
        print(f"FEHLER: Port {PORT} ist belegt oder der Server konnte nicht starten.")
        print(exc)
        print("Anderes Programm beenden oder Stop.bat ausführen, danach erneut Start.bat.")
        return 1
    finally:
        PID_FILE.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
