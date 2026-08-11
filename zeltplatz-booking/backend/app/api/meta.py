from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy.orm import Session
from fastapi import Depends

from app.countries import COUNTRIES
from app.database import get_db
from app.services.operator_settings import get_or_create_operator_settings

router = APIRouter(tags=["meta"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/countries")
def countries() -> list[dict[str, str]]:
    return COUNTRIES


@router.get("/meta")
def meta(db: Session = Depends(get_db)) -> dict:
    settings = get_or_create_operator_settings(db)
    return {
        "home_country": (settings.home_country or "AT").upper(),
        "countries": COUNTRIES,
    }
