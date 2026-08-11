from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Booking, BookingPitch, BookingService, Service
from app.schemas import BillingListItem
from app.services.billing import build_invoice

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("", response_model=list[BillingListItem])
def list_billing(
    from_date: date | None = None,
    to_date: date | None = None,
    db: Session = Depends(get_db),
) -> list[BillingListItem]:
    stmt = select(Booking).options(
        selectinload(Booking.booking_pitches).selectinload(BookingPitch.pitch),
        selectinload(Booking.persons),
        selectinload(Booking.booking_services)
        .selectinload(BookingService.service)
        .selectinload(Service.group),
        selectinload(Booking.custom_invoice_lines),
    )
    bookings = list(db.scalars(stmt).unique().all())
    if from_date is not None or to_date is not None:
        start = from_date or date.min
        end = to_date or date.max
        bookings = [b for b in bookings if b.start_date < end and start < b.end_date]
    bookings.sort(key=lambda b: b.start_date)
    items: list[BillingListItem] = []
    for booking in bookings:
        invoice = build_invoice(db, booking)
        items.append(
            BillingListItem(
                booking_id=booking.id,
                invoice_number=booking.invoice_number,
                group_name=booking.group_name,
                start_date=booking.start_date,
                end_date=booking.end_date,
                nights=invoice.nights,
                total=invoice.total,
            )
        )
    return items
