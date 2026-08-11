from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import PersonFeeBracket, PersonFeeElement, PriceProfile
from app.schemas import (
    PersonFeeBracketCreate,
    PersonFeeElementCreate,
    PersonFeeElementRead,
    PersonFeeElementUpdate,
)

router = APIRouter(prefix="/person-fee-elements", tags=["person-fees"])


def _validate_brackets(brackets: list[PersonFeeBracketCreate]) -> None:
    ordered = sorted(brackets, key=lambda b: b.age_from)
    for i, bracket in enumerate(ordered):
        if i == 0:
            continue
        prev = ordered[i - 1]
        if prev.age_to_exclusive is None:
            raise HTTPException(status_code=422, detail="Only the last bracket may be open-ended")
        if bracket.age_from < prev.age_to_exclusive:
            raise HTTPException(status_code=422, detail="Age brackets overlap")
        if bracket.age_from > prev.age_to_exclusive:
            raise HTTPException(status_code=422, detail="Age brackets have gaps")


def _to_read(element: PersonFeeElement) -> PersonFeeElementRead:
    return PersonFeeElementRead(
        id=element.id,
        price_profile_id=element.price_profile_id,
        name=element.name,
        kind=element.kind,
        daily_price=float(element.daily_price or 0),
        sort_order=element.sort_order,
        brackets=[
            {
                "id": b.id,
                "age_from": b.age_from,
                "age_to_exclusive": b.age_to_exclusive,
                "daily_price": float(b.daily_price or 0),
            }
            for b in element.brackets
        ],
    )


def _apply_brackets(element: PersonFeeElement, brackets: list[PersonFeeBracketCreate]) -> None:
    _validate_brackets(brackets)
    element.brackets.clear()
    for bracket in brackets:
        element.brackets.append(
            PersonFeeBracket(
                age_from=bracket.age_from,
                age_to_exclusive=bracket.age_to_exclusive,
                daily_price=bracket.daily_price,
            )
        )


@router.get("", response_model=list[PersonFeeElementRead])
def list_elements(
    price_profile_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[PersonFeeElementRead]:
    stmt = (
        select(PersonFeeElement)
        .options(selectinload(PersonFeeElement.brackets))
        .order_by(PersonFeeElement.sort_order, PersonFeeElement.name)
    )
    if price_profile_id is not None:
        stmt = stmt.where(PersonFeeElement.price_profile_id == price_profile_id)
    rows = list(db.scalars(stmt).all())
    return [_to_read(row) for row in rows]


@router.post("", response_model=PersonFeeElementRead, status_code=status.HTTP_201_CREATED)
def create_element(payload: PersonFeeElementCreate, db: Session = Depends(get_db)) -> PersonFeeElementRead:
    profile = db.get(PriceProfile, payload.price_profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Price profile not found")
    existing = db.scalar(
        select(PersonFeeElement).where(
            PersonFeeElement.price_profile_id == payload.price_profile_id,
            PersonFeeElement.name == payload.name,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Fee element name already exists in this profile")
    element = PersonFeeElement(
        price_profile_id=payload.price_profile_id,
        name=payload.name,
        kind=payload.kind,
        daily_price=payload.daily_price if payload.kind == "fixed" else 0,
        sort_order=payload.sort_order,
    )
    db.add(element)
    db.flush()
    if payload.kind == "age_based":
        _apply_brackets(element, payload.brackets)
    db.commit()
    element = db.scalar(
        select(PersonFeeElement)
        .where(PersonFeeElement.id == element.id)
        .options(selectinload(PersonFeeElement.brackets))
    )
    assert element is not None
    return _to_read(element)


@router.patch("/{element_id}", response_model=PersonFeeElementRead)
def update_element(
    element_id: int, payload: PersonFeeElementUpdate, db: Session = Depends(get_db)
) -> PersonFeeElementRead:
    element = db.scalar(
        select(PersonFeeElement)
        .where(PersonFeeElement.id == element_id)
        .options(selectinload(PersonFeeElement.brackets))
    )
    if not element:
        raise HTTPException(status_code=404, detail="Fee element not found")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        clash = db.scalar(
            select(PersonFeeElement).where(
                PersonFeeElement.price_profile_id == element.price_profile_id,
                PersonFeeElement.name == data["name"],
                PersonFeeElement.id != element_id,
            )
        )
        if clash:
            raise HTTPException(status_code=409, detail="Fee element name already exists in this profile")
        element.name = data["name"]
    if "kind" in data:
        element.kind = data["kind"]
    if "daily_price" in data:
        element.daily_price = data["daily_price"]
    if "sort_order" in data:
        element.sort_order = data["sort_order"]
    if element.kind == "fixed":
        element.brackets.clear()
        if "daily_price" not in data and element.daily_price is None:
            element.daily_price = 0
    if "brackets" in data and payload.brackets is not None:
        if element.kind != "age_based":
            raise HTTPException(status_code=422, detail="Brackets only allowed for age_based elements")
        _apply_brackets(element, payload.brackets)
    if element.kind == "age_based" and not element.brackets:
        raise HTTPException(status_code=422, detail="age_based elements require at least one bracket")
    db.commit()
    element = db.scalar(
        select(PersonFeeElement)
        .where(PersonFeeElement.id == element_id)
        .options(selectinload(PersonFeeElement.brackets))
    )
    assert element is not None
    return _to_read(element)


@router.delete("/{element_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_element(element_id: int, db: Session = Depends(get_db)) -> None:
    element = db.get(PersonFeeElement, element_id)
    if not element:
        raise HTTPException(status_code=404, detail="Fee element not found")
    db.delete(element)
    db.commit()
