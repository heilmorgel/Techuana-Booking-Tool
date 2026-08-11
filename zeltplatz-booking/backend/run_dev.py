"""Local development entrypoint (no Home Assistant required)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent / ".data"
DATA.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("DATA_DIR", str(DATA))
os.environ.setdefault("DEV_MODE", "1")
os.environ.setdefault("TZ", "Europe/Vienna")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
