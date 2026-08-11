from __future__ import annotations

from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Booking, BookingPitch, Pitch


def intervals_overlap(a_start: date, a_end: date, b_start: date, b_end: date) -> bool:
    """Half-open intervals [start, end) overlap check."""
    return a_start < b_end and b_start < a_end


def pitch_covers_range(pitch: Pitch, start: date, end: date) -> bool:
    exclusive_pitch_end = pitch.available_to + timedelta(days=1)
    return pitch.available_from <= start and end <= exclusive_pitch_end


def find_overlapping_pitch_segments(
    db: Session,
    pitch_ids: list[int],
    start: date,
    end: date,
    exclude_booking_id: int | None = None,
) -> list[BookingPitch]:
    stmt = (
        select(BookingPitch)
        .where(BookingPitch.pitch_id.in_(pitch_ids))
        .options(selectinload(BookingPitch.pitch), selectinload(BookingPitch.booking))
    )
    if exclude_booking_id is not None:
        stmt = stmt.where(BookingPitch.booking_id != exclude_booking_id)
    segments = list(db.scalars(stmt).all())
    return [s for s in segments if intervals_overlap(start, end, s.start_date, s.end_date)]


def find_overlapping_bookings(
    db: Session,
    pitch_ids: list[int],
    start: date,
    end: date,
    exclude_booking_id: int | None = None,
) -> list[Booking]:
    segments = find_overlapping_pitch_segments(
        db, pitch_ids, start, end, exclude_booking_id=exclude_booking_id
    )
    by_id: dict[int, Booking] = {}
    for seg in segments:
        by_id[seg.booking_id] = seg.booking
    return list(by_id.values())


def list_available_pitches(
    db: Session,
    start: date,
    end: date,
    exclude_booking_id: int | None = None,
) -> list[Pitch]:
    if start >= end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start must be before end",
        )
    pitches = list(db.scalars(select(Pitch).order_by(Pitch.name)).all())
    available: list[Pitch] = []
    for pitch in pitches:
        if not pitch_covers_range(pitch, start, end):
            continue
        overlaps = find_overlapping_pitch_segments(
            db, [pitch.id], start, end, exclude_booking_id=exclude_booking_id
        )
        if not overlaps:
            available.append(pitch)
    return available


def assert_pitches_bookable(
    db: Session,
    pitch_ids: list[int],
    start: date,
    end: date,
    exclude_booking_id: int | None = None,
) -> list[Pitch]:
    if not pitch_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one pitch required",
        )
    if len(set(pitch_ids)) != len(pitch_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Duplicate pitch ids",
        )

    pitches = list(db.scalars(select(Pitch).where(Pitch.id.in_(pitch_ids))).all())
    if len(pitches) != len(pitch_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more pitches not found")

    for pitch in pitches:
        if not pitch_covers_range(pitch, start, end):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Pitch '{pitch.name}' is not available for the selected date range",
            )

    overlaps = find_overlapping_pitch_segments(
        db, pitch_ids, start, end, exclude_booking_id=exclude_booking_id
    )
    if overlaps:
        names = ", ".join(sorted({s.pitch.name for s in overlaps if s.pitch}))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Date range overlaps existing booking on: {names}",
        )
    return pitches


def pitch_ids_active_from(booking: Booking, effective: date) -> list[int]:
    """Pitches that have a segment overlapping [effective, booking.end_date)."""
    ids: list[int] = []
    seen: set[int] = set()
    for seg in booking.booking_pitches:
        if intervals_overlap(effective, booking.end_date, seg.start_date, seg.end_date):
            if seg.pitch_id not in seen:
                seen.add(seg.pitch_id)
                ids.append(seg.pitch_id)
    return ids
