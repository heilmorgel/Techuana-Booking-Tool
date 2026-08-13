from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api import (
    billing,
    bookings,
    meta,
    operator_settings,
    person_fees,
    pitches,
    price_profiles,
    service_groups,
    services,
)
from app.auth import ApiTokenMiddleware
from app.database import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
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
api.include_router(price_profiles.router)
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

    _user_index = _static_dir / "index.html"
    _admin_index = _static_dir / "admin" / "index.html"

    @app.get("/{full_path:path}", response_model=None)
    async def spa_fallback(full_path: str):
        if full_path == "admin":
            return RedirectResponse(url="/admin/")
        candidate = _static_dir / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        if full_path.startswith("admin/"):
            if _admin_index.is_file():
                return FileResponse(_admin_index)
        return FileResponse(_user_index)
