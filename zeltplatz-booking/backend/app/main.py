from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import (
    billing,
    bookings,
    meta,
    operator_settings,
    person_fees,
    pitches,
    service_groups,
    services,
)
from app.auth import ApiTokenMiddleware
from app.database import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    # #region agent log
    try:
        import json, time
        from pathlib import Path
        paths = sorted(api.openapi().get("paths", {}).keys())
        payload = {
            "sessionId": "188c80",
            "runId": "pre-fix",
            "hypothesisId": "A",
            "location": "main.py:lifespan",
            "message": "api routes at startup",
            "data": {
                "has_operator": any("operator-settings" in p for p in paths),
                "operator_paths": [p for p in paths if "operator" in p],
                "route_count": len(paths),
            },
            "timestamp": int(time.time() * 1000),
        }
        log_path = Path(__file__).resolve().parents[3] / ".cursor" / "debug-188c80.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception as e:
        try:
            log_path = Path(__file__).resolve().parents[3] / ".cursor" / "debug-188c80.log"
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"188c80","hypothesisId":"A","location":"main.py:lifespan","message":"log failed","data":{"error":str(e)},"timestamp":int(__import__('time').time()*1000)})+"\n")
        except Exception:
            pass
    # #endregion
    yield


app = FastAPI(title="Zeltplatz Buchung", version="0.1.0", lifespan=lifespan)
app.add_middleware(ApiTokenMiddleware)

api = FastAPI()
api.include_router(meta.router)
api.include_router(pitches.router)
api.include_router(bookings.router)
api.include_router(service_groups.router)
api.include_router(services.router)
api.include_router(person_fees.router)
api.include_router(billing.router)
api.include_router(operator_settings.router)
app.mount("/api/v1", api)

# Also expose /api/health for simpler probes
app.include_router(meta.router, prefix="/api")


# Static frontend (production / add-on build)
_STATIC_CANDIDATES = [
    Path(__file__).resolve().parents[2] / "frontend" / "dist",
    Path("/app/frontend/dist"),
]
_static_dir = next((p for p in _STATIC_CANDIDATES if p.is_dir()), None)

if _static_dir is not None:
    assets = _static_dir / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse:
        candidate = _static_dir / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_static_dir / "index.html")
