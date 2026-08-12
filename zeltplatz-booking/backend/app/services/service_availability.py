from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Booking, BookingService, Service
from app.services.availability import intervals_overlap


def peak_usage(
    db: Session,
    service_id: int,
    start: date,
    end: date,
    exclude_booking_id: int | None = None,
) -> int:
    """Max concurrent quantity of a service over half-open [start, end)."""
    if start >= end:
        return 0

    stmt = (
        select(BookingService)
        .where(BookingService.service_id == service_id)
        .options(selectinload(BookingService.booking), selectinload(BookingService.service))
    )
    rows = list(db.scalars(stmt).all())
    intervals: list[tuple[date, date, int]] = []
    for row in rows:
        if exclude_booking_id is not None and row.booking_id == exclude_booking_id:
            continue
        if not intervals_overlap(start, end, row.start_date, row.end_date):
            continue
        intervals.append((row.start_date, row.end_date, row.quantity))

    if not intervals:
        return 0

    peak = 0
    cursor = start
    while cursor < end:
        day_end = cursor + timedelta(days=1)
        used = sum(
            qty
            for b_start, b_end, qty in intervals
            if intervals_overlap(cursor, day_end, b_start, b_end)
        )
        if used > peak:
            peak = used
        cursor = day_end
    return peak


def check_services(
    db: Session,
    start: date,
    end: date,
    requested: list[tuple[int, int]],
    exclude_booking_id: int | None = None,
) -> list[str]:
    """Return soft-warning messages when requested quantities would overbook stock."""
    warnings: list[str] = []
    for service_id, quantity in requested:
        if quantity <= 0:
            continue
        service = db.get(Service, service_id)
        if service is None:
            warnings.append(f"Unbekannter Dienst (ID {service_id})")
            continue
        used = peak_usage(db, service_id, start, end, exclude_booking_id=exclude_booking_id)
        total_need = used + quantity
        if total_need > service.available_quantity:
            warnings.append(
                f"{service.name}: Bedarf {total_need}, Bestand {service.available_quantity} "
                f"(bereits verplant {used})"
            )
    return warnings


def service_availability_rows(
    db: Session,
    start: date,
    end: date,
    exclude_booking_id: int | None = None,
) -> list[dict]:
    services = list(
        db.scalars(select(Service).options(selectinload(Service.group)).order_by(Service.name)).all()
    )
    rows: list[dict] = []
    for service in services:
        used = peak_usage(db, service.id, start, end, exclude_booking_id=exclude_booking_id)
        remaining = service.available_quantity - used
        rows.append(
            {
                "service_id": service.id,
                "name": service.name,
                "group_id": service.group_id,
                "group_name": service.group.name if service.group else "",
                "available_quantity": service.available_quantity,
                "daily_price": float(service.daily_price or 0),
                "deposit": float(service.deposit or 0),
                "used": used,
                "remaining": remaining,
            }
        )
    return rows


def service_qty_from(booking: Booking, effective: date) -> dict[int, int]:
    """Quantity per service_id active on/after effective (segment covering effective)."""
    result: dict[int, int] = {}
    for row in booking.booking_services:
        if row.start_date <= effective < row.end_date:
            result[row.service_id] = row.quantity
    return result
