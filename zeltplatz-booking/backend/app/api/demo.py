from __future__ import annotations

from fastapi import APIRouter

from app.schemas import DemoResetResult
from app.services.demo_seed import reset_and_seed

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/reset", response_model=DemoResetResult)
def reset_demo() -> DemoResetResult:
    return DemoResetResult(**reset_and_seed())
