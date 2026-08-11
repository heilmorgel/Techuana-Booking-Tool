"""Assign unique invoice numbers: YYYYMMDD-NNNN (date + daily sequence)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Booking

_MAX_RETRIES = 5


def format_invoice_number(on_date: date, sequence: int) -> str:
    return f"{on_date.strftime('%Y%m%d')}-{sequence:04d}"


def _next_sequence_for_day(db: Session, on_date: date) -> int:
    prefix = on_date.strftime("%Y%m%d")
    existing = db.scalars(
        select(Booking.invoice_number).where(Booking.invoice_number.like(f"{prefix}-%"))
    ).all()
    max_seq = 0
    for number in existing:
        if not number:
            continue
        try:
            seq = int(number.rsplit("-", 1)[-1])
        except ValueError:
            continue
        if seq > max_seq:
            max_seq = seq
    return max_seq + 1


def ensure_invoice_number(
    db: Session,
    booking: Booking,
    *,
    on_date: date | None = None,
) -> str:
    """Persist a unique invoice number on first access; return the stored value thereafter."""
    if booking.invoice_number:
        return booking.invoice_number

    day = on_date or date.today()
    last_error: Exception | None = None
    for _ in range(_MAX_RETRIES):
        seq = _next_sequence_for_day(db, day)
        candidate = format_invoice_number(day, seq)
        booking.invoice_number = candidate
        try:
            db.add(booking)
            db.commit()
            db.refresh(booking)
            return booking.invoice_number
        except IntegrityError as exc:
            db.rollback()
            last_error = exc
            fresh = db.get(Booking, booking.id)
            if fresh is not None and fresh.invoice_number:
                booking.invoice_number = fresh.invoice_number
                return fresh.invoice_number
            booking.invoice_number = None

    raise RuntimeError("Could not assign unique invoice number") from last_error
