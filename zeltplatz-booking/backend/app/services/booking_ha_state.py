"""Classify bookings for Home Assistant MQTT entities."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Booking, BookingPitch
from app.services.availability import intervals_overlap


@dataclass(frozen=True)
class BookingHaItem:
    id: int
    group_name: str
    start_date: str
    end_date: str
    pitch_names: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class BookingHaSnapshot:
    active: list[BookingHaItem]
    arrivals: list[BookingHaItem]
    departures: list[BookingHaItem]

    @property
    def active_count(self) -> int:
        return len(self.active)

    @property
    def arrivals_count(self) -> int:
        return len(self.arrivals)

    @property
    def departures_count(self) -> int:
        return len(self.departures)


def is_active(booking: Booking, today: date) -> bool:
    """On-site: half-open interval [start_date, end_date)."""
    return booking.start_date <= today < booking.end_date


def is_arrival_today(booking: Booking, today: date) -> bool:
    return booking.start_date == today


def is_departure_today(booking: Booking, today: date) -> bool:
    return booking.end_date == today


def pitch_names_as_of(booking: Booking, as_of: date) -> list[str]:
    """Pitch names with a segment covering [as_of, as_of+1)."""
    day_end = as_of + timedelta(days=1)
    names: list[str] = []
    seen: set[str] = set()
    for seg in booking.booking_pitches:
        if not intervals_overlap(as_of, day_end, seg.start_date, seg.end_date):
            continue
        name = seg.pitch.name if seg.pitch else str(seg.pitch_id)
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def booking_to_ha_item(booking: Booking, as_of: date) -> BookingHaItem:
    return BookingHaItem(
        id=booking.id,
        group_name=booking.group_name,
        start_date=booking.start_date.isoformat(),
        end_date=booking.end_date.isoformat(),
        pitch_names=pitch_names_as_of(booking, as_of),
    )


def classify_bookings(bookings: list[Booking], today: date) -> BookingHaSnapshot:
    active: list[BookingHaItem] = []
    arrivals: list[BookingHaItem] = []
    departures: list[BookingHaItem] = []

    for booking in sorted(bookings, key=lambda b: (b.start_date, b.group_name, b.id)):
        if is_active(booking, today):
            active.append(booking_to_ha_item(booking, today))
        if is_arrival_today(booking, today):
            arrivals.append(booking_to_ha_item(booking, today))
        if is_departure_today(booking, today):
            last_night = booking.end_date - timedelta(days=1)
            departures.append(booking_to_ha_item(booking, last_night))

    return BookingHaSnapshot(active=active, arrivals=arrivals, departures=departures)


def load_booking_ha_snapshot(db: Session, today: date | None = None) -> BookingHaSnapshot:
    today = today or date.today()
    bookings = list(
        db.scalars(
            select(Booking).options(
                selectinload(Booking.booking_pitches).selectinload(BookingPitch.pitch),
            )
        ).all()
    )
    return classify_bookings(bookings, today)
