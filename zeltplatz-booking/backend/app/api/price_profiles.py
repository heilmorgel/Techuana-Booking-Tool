from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Person, PriceProfile
from app.schemas import PriceProfileCreate, PriceProfileRead, PriceProfileUpdate

router = APIRouter(prefix="/price-profiles", tags=["price-profiles"])


def get_default_profile(db: Session) -> PriceProfile | None:
    return db.scalar(select(PriceProfile).where(PriceProfile.is_default.is_(True)))


def require_default_profile(db: Session) -> PriceProfile:
    profile = get_default_profile(db)
    if profile is None:
        raise HTTPException(status_code=500, detail="No default price profile configured")
    return profile


def _clear_other_defaults(db: Session, keep_id: int) -> None:
    db.execute(
        update(PriceProfile)
        .where(PriceProfile.id != keep_id, PriceProfile.is_default.is_(True))
        .values(is_default=False)
    )


def _ensure_one_default(db: Session) -> None:
    default = get_default_profile(db)
    if default is not None:
        return
    first = db.scalar(select(PriceProfile).order_by(PriceProfile.sort_order, PriceProfile.name))
    if first is not None:
        first.is_default = True


@router.get("", response_model=list[PriceProfileRead])
def list_profiles(db: Session = Depends(get_db)) -> list[PriceProfile]:
    return list(
        db.scalars(
            select(PriceProfile).order_by(PriceProfile.sort_order, PriceProfile.name)
        ).all()
    )


@router.post("", response_model=PriceProfileRead, status_code=status.HTTP_201_CREATED)
def create_profile(payload: PriceProfileCreate, db: Session = Depends(get_db)) -> PriceProfile:
    existing = db.scalar(select(PriceProfile).where(PriceProfile.name == payload.name))
    if existing:
        raise HTTPException(status_code=409, detail="Price profile name already exists")
    profile = PriceProfile(
        name=payload.name,
        is_default=payload.is_default,
        sort_order=payload.sort_order,
    )
    db.add(profile)
    db.flush()
    if profile.is_default:
        _clear_other_defaults(db, profile.id)
    else:
        _ensure_one_default(db)
    db.commit()
    db.refresh(profile)
    return profile


@router.patch("/{profile_id}", response_model=PriceProfileRead)
def update_profile(
    profile_id: int, payload: PriceProfileUpdate, db: Session = Depends(get_db)
) -> PriceProfile:
    profile = db.get(PriceProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Price profile not found")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        clash = db.scalar(
            select(PriceProfile).where(
                PriceProfile.name == data["name"], PriceProfile.id != profile_id
            )
        )
        if clash:
            raise HTTPException(status_code=409, detail="Price profile name already exists")
        profile.name = data["name"]
    if "sort_order" in data:
        profile.sort_order = data["sort_order"]
    if "is_default" in data:
        if data["is_default"]:
            profile.is_default = True
            _clear_other_defaults(db, profile.id)
        elif profile.is_default:
            raise HTTPException(
                status_code=422,
                detail="Cannot unset default; mark another profile as default instead",
            )
    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(profile_id: int, db: Session = Depends(get_db)) -> None:
    profile = db.get(PriceProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Price profile not found")
    total = db.scalar(select(func.count()).select_from(PriceProfile)) or 0
    if total <= 1:
        raise HTTPException(status_code=422, detail="Cannot delete the last price profile")
    in_use = db.scalar(
        select(func.count()).select_from(Person).where(Person.price_profile_id == profile_id)
    )
    if in_use:
        raise HTTPException(
            status_code=409,
            detail="Price profile is still used by persons and cannot be deleted",
        )
    was_default = profile.is_default
    db.delete(profile)
    db.flush()
    if was_default:
        _ensure_one_default(db)
    db.commit()
