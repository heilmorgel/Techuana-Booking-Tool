from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Booking, Pitch
from app.schemas import PitchCreate, PitchRead, PitchUpdate, BookingRead
from app.api.bookings import booking_to_read
from app.services.availability import list_available_pitches

router = APIRouter(prefix="/pitches", tags=["pitches"])


@router.get("/available", response_model=list[PitchRead])
def get_available_pitches(
    start: str,
    end: str,
    exclude_booking_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[Pitch]:
    from datetime import date

    try:
        start_d = date.fromisoformat(start)
        end_d = date.fromisoformat(end)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid date format, use YYYY-MM-DD") from exc
    return list_available_pitches(
        db, start_d, end_d, exclude_booking_id=exclude_booking_id
    )


@router.get("", response_model=list[PitchRead])
def list_pitches(db: Session = Depends(get_db)) -> list[Pitch]:
    return list(db.scalars(select(Pitch).order_by(Pitch.name)).all())


@router.post("", response_model=PitchRead, status_code=status.HTTP_201_CREATED)
def create_pitch(payload: PitchCreate, db: Session = Depends(get_db)) -> Pitch:
    existing = db.scalar(select(Pitch).where(Pitch.name == payload.name))
    if existing:
        raise HTTPException(status_code=409, detail="Pitch name already exists")
    pitch = Pitch(**payload.model_dump())
    db.add(pitch)
    db.commit()
    db.refresh(pitch)
    return pitch


@router.get("/{pitch_id}", response_model=PitchRead)
def get_pitch(pitch_id: int, db: Session = Depends(get_db)) -> Pitch:
    pitch = db.get(Pitch, pitch_id)
    if not pitch:
        raise HTTPException(status_code=404, detail="Pitch not found")
    return pitch


@router.patch("/{pitch_id}", response_model=PitchRead)
def update_pitch(pitch_id: int, payload: PitchUpdate, db: Session = Depends(get_db)) -> Pitch:
    pitch = db.get(Pitch, pitch_id)
    if not pitch:
        raise HTTPException(status_code=404, detail="Pitch not found")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        clash = db.scalar(select(Pitch).where(Pitch.name == data["name"], Pitch.id != pitch_id))
        if clash:
            raise HTTPException(status_code=409, detail="Pitch name already exists")
    for key, value in data.items():
        setattr(pitch, key, value)
    if pitch.available_from >= pitch.available_to:
        raise HTTPException(status_code=422, detail="available_from must be before available_to")
    db.commit()
    db.refresh(pitch)
    return pitch


@router.delete("/{pitch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pitch(pitch_id: int, db: Session = Depends(get_db)) -> None:
    pitch = db.get(Pitch, pitch_id)
    if not pitch:
        raise HTTPException(status_code=404, detail="Pitch not found")
    from app.models import BookingPitch

    linked = db.scalar(select(BookingPitch).where(BookingPitch.pitch_id == pitch_id).limit(1))
    if linked:
        raise HTTPException(
            status_code=409,
            detail="Pitch has bookings and cannot be deleted",
        )
    db.delete(pitch)
    db.commit()


@router.get("/{pitch_id}/bookings", response_model=list[BookingRead])
def list_pitch_bookings(pitch_id: int, db: Session = Depends(get_db)) -> list[BookingRead]:
    pitch = db.get(Pitch, pitch_id)
    if not pitch:
        raise HTTPException(status_code=404, detail="Pitch not found")
    from app.models import BookingPitch, BookingService, Service

    bookings = list(
        db.scalars(
            select(Booking)
            .join(BookingPitch)
            .where(BookingPitch.pitch_id == pitch_id)
            .options(
                selectinload(Booking.booking_pitches).selectinload(BookingPitch.pitch),
                selectinload(Booking.persons),
                selectinload(Booking.booking_services)
                .selectinload(BookingService.service)
                .selectinload(Service.group),
                selectinload(Booking.amendments),
            )
            .order_by(Booking.start_date)
        )
        .unique()
        .all()
    )
    return [booking_to_read(b) for b in bookings]
