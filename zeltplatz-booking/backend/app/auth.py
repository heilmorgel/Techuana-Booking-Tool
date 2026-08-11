from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings


def _client_is_trusted(request: Request) -> bool:
    """Allow HA ingress and local development without API token."""
    settings = get_settings()
    if settings.dev_mode:
        return True

    host = (request.client.host if request.client else "") or ""
    if host in ("127.0.0.1", "::1", "localhost"):
        return True

    # Home Assistant ingress sets these headers
    if request.headers.get("x-hass-source") or request.headers.get("x-forwarded-host"):
        return True

    return False


class ApiTokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # noqa: ANN001
        path = request.url.path
        if path == "/api/health" or path == "/health" or not path.startswith("/api/"):
            return await call_next(request)

        settings = get_settings()
        configured = (settings.api_token or "").strip()
        if not configured:
            return await call_next(request)

        if _client_is_trusted(request):
            return await call_next(request)

        provided = request.headers.get("x-api-token", "")
        if provided != configured:
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing API token"})

        return await call_next(request)
