from __future__ import annotations

from fastapi import APIRouter

from app.countries import COUNTRIES

router = APIRouter(tags=["meta"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/countries")
def countries() -> list[dict[str, str]]:
    return COUNTRIES
