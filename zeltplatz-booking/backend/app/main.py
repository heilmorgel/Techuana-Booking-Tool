from __future__ import annotations

import json
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
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

# #region agent log
_DEBUG_LOG_CANDIDATES = [
    Path(__file__).resolve().parents[3] / "debug-3650c0.log",
    Path("/data/debug-3650c0.log"),
    Path("/tmp/debug-3650c0.log"),
]


def _agent_log(hypothesis_id: str, location: str, message: str, data: dict | None = None) -> None:
    payload = {
        "sessionId": "3650c0",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data or {},
        "timestamp": int(time.time() * 1000),
    }
    line = json.dumps(payload, ensure_ascii=True)
    print(f"DEBUG_ZELT {line}", flush=True)
    for path in _DEBUG_LOG_CANDIDATES:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
            break
        except OSError:
            continue


# #endregion


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    # #region agent log
    _agent_log(
        "A",
        "main.py:lifespan",
        "static_dir_resolved",
        {
            "static_dir": str(_static_dir) if _static_dir else None,
            "static_exists": bool(_static_dir and _static_dir.is_dir()),
            "index_exists": bool(_static_dir and (_static_dir / "index.html").is_file()),
            "admin_index_exists": bool(
                _static_dir and (_static_dir / "admin" / "index.html").is_file()
            ),
            "assets_exists": bool(_static_dir and (_static_dir / "assets").is_dir()),
            "asset_count": (
                len(list((_static_dir / "assets").glob("*")))
                if _static_dir and (_static_dir / "assets").is_dir()
                else 0
            ),
        },
    )
    # #endregion
    yield


app = FastAPI(title="Zeltplatz Buchung", version="0.1.0", lifespan=lifespan)
app.add_middleware(ApiTokenMiddleware)


# #region agent log
@app.middleware("http")
async def _debug_request_middleware(request: Request, call_next):  # noqa: ANN001
    path = request.url.path
    interesting = path in ("/", "/admin", "/admin/") or path.startswith("/assets/")
    if interesting:
        _agent_log(
            "B",
            "main.py:middleware",
            "incoming_ui_request",
            {
                "path": path,
                "root_path": request.scope.get("root_path", ""),
                "x_forwarded_prefix": request.headers.get("x-forwarded-prefix"),
                "x_ingress_path": request.headers.get("x-ingress-path"),
                "x_forwarded_host": request.headers.get("x-forwarded-host"),
                "x_forwarded_for": request.headers.get("x-forwarded-for"),
                "referer": request.headers.get("referer"),
                "host": request.headers.get("host"),
            },
        )
    response = await call_next(request)
    if interesting:
        _agent_log(
            "B",
            "main.py:middleware",
            "ui_response",
            {"path": path, "status": response.status_code},
        )
    return response


# #endregion

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
        # #region agent log
        _agent_log(
            "A",
            "main.py:spa_fallback",
            "spa_fallback_hit",
            {"full_path": full_path},
        )
        # #endregion
        if full_path == "admin":
            return RedirectResponse(url="/admin/")
        candidate = _static_dir / full_path
        if full_path and candidate.is_file():
            # #region agent log
            _agent_log(
                "A",
                "main.py:spa_fallback",
                "serving_static_file",
                {"full_path": full_path, "file": str(candidate)},
            )
            # #endregion
            return FileResponse(candidate)
        if full_path.startswith("admin/"):
            if _admin_index.is_file():
                # #region agent log
                content = _admin_index.read_text(encoding="utf-8")
                _agent_log(
                    "C",
                    "main.py:spa_fallback",
                    "serving_admin_index",
                    {
                        "has_abs_assets": '/assets/' in content,
                        "script_src_sample": content[
                            content.find("src=") : content.find("src=") + 60
                        ]
                        if "src=" in content
                        else None,
                    },
                )
                # #endregion
                return FileResponse(_admin_index)
        # #region agent log
        content = _user_index.read_text(encoding="utf-8") if _user_index.is_file() else ""
        _agent_log(
            "C",
            "main.py:spa_fallback",
            "serving_user_index",
            {
                "has_abs_assets": "/assets/" in content,
                "script_src_sample": content[content.find("src=") : content.find("src=") + 60]
                if "src=" in content
                else None,
            },
        )
        # #endregion
        return FileResponse(_user_index)
