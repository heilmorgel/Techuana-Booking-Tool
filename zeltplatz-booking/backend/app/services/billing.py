from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Booking, BookingPitch, BookingService, PersonFeeElement, Service
from app.services.invoice_number import ensure_invoice_number
from app.services.operator_settings import get_or_create_operator_settings, operator_to_invoice
from app.schemas import InvoiceLine, InvoiceRead


def _money(value: float | Decimal) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def age_on_date(birth_date: date, on_date: date) -> int:
    years = on_date.year - birth_date.year
    if (on_date.month, on_date.day) < (birth_date.month, birth_date.day):
        years -= 1
    return max(years, 0)


def nights_for(booking: Booking) -> int:
    return max((booking.end_date - booking.start_date).days, 0)


def nights_between(start: date, end: date) -> int:
    return max((end - start).days, 0)


def rate_for_element(element: PersonFeeElement, age: int) -> float | None:
    if element.kind == "fixed":
        return float(element.daily_price or 0)
    for bracket in element.brackets:
        upper = bracket.age_to_exclusive
        if age >= bracket.age_from and (upper is None or age < upper):
            return float(bracket.daily_price or 0)
    return None


def build_invoice(
    db: Session,
    booking: Booking,
    *,
    assign_number: bool = False,
) -> InvoiceRead:
    nights = nights_for(booking)
    invoice_number: str | None = booking.invoice_number
    if assign_number:
        invoice_number = ensure_invoice_number(db, booking)
    lines: list[InvoiceLine] = []

    segments = sorted(
        booking.booking_pitches,
        key=lambda s: ((s.pitch.name if s.pitch else ""), s.start_date),
    )
    for seg in segments:
        unit = float(seg.pitch.daily_price or 0) if seg.pitch else 0
        seg_nights = nights_between(seg.start_date, seg.end_date)
        amount = _money(unit * seg_nights)
        name = seg.pitch.name if seg.pitch else f"#{seg.pitch_id}"
        lines.append(
            InvoiceLine(
                category="pitch",
                label=f"Zeltplatz {name}",
                quantity=1,
                unit_price=unit,
                nights=seg_nights,
                amount=amount,
                start_date=seg.start_date,
                end_date=seg.end_date,
            )
        )

    elements_by_profile: dict[int, list[PersonFeeElement]] = {}
    profile_ids = {person.price_profile_id for person in booking.persons}
    if profile_ids:
        all_elements = list(
            db.scalars(
                select(PersonFeeElement)
                .where(PersonFeeElement.price_profile_id.in_(profile_ids))
                .options(selectinload(PersonFeeElement.brackets))
                .order_by(PersonFeeElement.sort_order, PersonFeeElement.name)
            ).all()
        )
        for element in all_elements:
            elements_by_profile.setdefault(element.price_profile_id, []).append(element)

    for person in booking.persons:
        person_start = person.start_date
        person_nights = nights_between(person.start_date, person.end_date)
        age = age_on_date(person.birth_date, person_start)
        daily_total = 0.0
        for element in elements_by_profile.get(person.price_profile_id, []):
            rate = rate_for_element(element, age)
            if rate is None:
                continue
            daily_total += rate
        if daily_total <= 0:
            continue
        amount = _money(daily_total * person_nights)
        lines.append(
            InvoiceLine(
                category="person",
                label=f"{person.name} ({age} J.)",
                quantity=1,
                unit_price=_money(daily_total),
                nights=person_nights,
                amount=amount,
                start_date=person.start_date,
                end_date=person.end_date,
            )
        )

    for bs in sorted(booking.booking_services, key=lambda r: (r.service.name if r.service else "", r.start_date)):
        service = bs.service
        if service is None:
            continue
        unit = float(service.daily_price or 0)
        qty = bs.quantity
        seg_nights = nights_between(bs.start_date, bs.end_date)
        amount = _money(unit * qty * seg_nights)
        lines.append(
            InvoiceLine(
                category="service",
                label=f"{service.name} × {qty}",
                quantity=qty,
                unit_price=unit,
                nights=seg_nights,
                amount=amount,
                start_date=bs.start_date,
                end_date=bs.end_date,
            )
        )

    for custom in booking.custom_invoice_lines:
        amount = _money(custom.amount)
        lines.append(
            InvoiceLine(
                id=custom.id,
                category="custom",
                label=custom.label,
                quantity=1,
                unit_price=amount,
                nights=0,
                amount=amount,
            )
        )

    # Auto lines only if amount > 0; custom lines always (incl. 0 notes / negative discounts)
    visible = [
        line for line in lines if line.category == "custom" or line.amount > 0
    ]
    total = _money(sum(line.amount for line in visible))
    operator = operator_to_invoice(get_or_create_operator_settings(db))
    return InvoiceRead(
        booking_id=booking.id,
        invoice_number=invoice_number,
        group_name=booking.group_name,
        start_date=booking.start_date,
        end_date=booking.end_date,
        nights=nights,
        lines=visible,
        total=total,
        operator=operator,
    )


def load_booking_for_invoice(db: Session, booking_id: int) -> Booking | None:
    return db.scalar(
        select(Booking)
        .where(Booking.id == booking_id)
        .options(
            selectinload(Booking.booking_pitches).selectinload(BookingPitch.pitch),
            selectinload(Booking.persons),
            selectinload(Booking.booking_services)
            .selectinload(BookingService.service)
            .selectinload(Service.group),
            selectinload(Booking.custom_invoice_lines),
        )
    )
