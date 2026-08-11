from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.countries import VALID_NATIONALITY_CODES
from app.database import get_db
from app.models import Booking, BookingPitch, BookingService, Person, Service
from app.schemas import (
    BookingAmendRequest,
    BookingAmendmentRead,
    BookingCreate,
    BookingGanttItem,
    BookingPitchSegmentRead,
    BookingRead,
    BookingServiceRead,
    BookingUpdate,
    InvoiceRead,
    PersonCreate,
)
from app.services.amendments import apply_amendment
from app.services.availability import assert_pitches_bookable, pitch_ids_active_from
from app.services.billing import build_invoice, load_booking_for_invoice
from app.services.invoice_pdf import render_invoice_pdf
from app.services.operator_settings import get_or_create_operator_settings, logo_path
from app.services.service_availability import check_services

router = APIRouter(prefix="/bookings", tags=["bookings"])


def _booking_fully_editable(booking: Booking) -> bool:
    return date.today() <= booking.start_date


def _booking_amendable(booking: Booking) -> bool:
    today = date.today()
    return booking.start_date < today < booking.end_date


def _validate_persons(
    persons: list[PersonCreate],
    booking_start: date,
    booking_end: date,
) -> None:
    for person in persons:
        if person.nationality not in VALID_NATIONALITY_CODES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid nationality code: {person.nationality}",
            )
        start = person.start_date or booking_start
        end = person.end_date or booking_end
        if start >= end:
            raise HTTPException(
                status_code=422,
                detail=f"Person '{person.name}': Anreise muss vor Abreise liegen",
            )
        if start < booking_start or end > booking_end:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Person '{person.name}': Zeitraum muss innerhalb "
                    f"der Buchung ({booking_start}–{booking_end}) liegen"
                ),
            )


def _person_model(person: PersonCreate, booking_start: date, booking_end: date) -> Person:
    return Person(
        name=person.name,
        birth_date=person.birth_date,
        nationality=person.nationality,
        start_date=person.start_date or booking_start,
        end_date=person.end_date or booking_end,
    )


def _normalize_services(items: list) -> list[tuple[int, int]]:
    merged: dict[int, int] = {}
    for item in items:
        merged[item.service_id] = merged.get(item.service_id, 0) + item.quantity
    return [(sid, qty) for sid, qty in merged.items() if qty > 0]


def _resolve_booking_services(
    db: Session, items: list, start: date, end: date
) -> list[BookingService]:
    normalized = _normalize_services(items)
    result: list[BookingService] = []
    for service_id, quantity in normalized:
        service = db.get(Service, service_id)
        if not service:
            raise HTTPException(status_code=404, detail=f"Service {service_id} not found")
        result.append(
            BookingService(
                service_id=service_id,
                quantity=quantity,
                start_date=start,
                end_date=end,
            )
        )
    return result


def booking_to_read(booking: Booking, warnings: list[str] | None = None) -> BookingRead:
    services: list[BookingServiceRead] = []
    for bs in booking.booking_services:
        services.append(
            BookingServiceRead(
                service_id=bs.service_id,
                quantity=bs.quantity,
                service_name=bs.service.name if bs.service else "",
                group_name=bs.service.group.name if bs.service and bs.service.group else "",
                daily_price=float(bs.service.daily_price or 0) if bs.service else 0,
                start_date=bs.start_date,
                end_date=bs.end_date,
            )
        )
    segments = [
        BookingPitchSegmentRead(
            pitch_id=seg.pitch_id,
            pitch_name=seg.pitch.name if seg.pitch else "",
            start_date=seg.start_date,
            end_date=seg.end_date,
        )
        for seg in booking.booking_pitches
    ]
    today = date.today()
    if today < booking.start_date:
        as_of = booking.start_date
    elif today >= booking.end_date:
        as_of = booking.start_date
    else:
        as_of = today
    pitch_ids = pitch_ids_active_from(booking, as_of)
    if not pitch_ids:
        pitch_ids = list(dict.fromkeys(s.pitch_id for s in booking.booking_pitches))

    amendments = [
        BookingAmendmentRead(
            id=a.id,
            effective_date=a.effective_date,
            created_at=a.created_at,
            summary=a.summary,
            diff_json=a.diff_json,
        )
        for a in booking.amendments
    ]
    return BookingRead(
        id=booking.id,
        group_name=booking.group_name,
        start_date=booking.start_date,
        end_date=booking.end_date,
        created_at=booking.created_at,
        notes=booking.notes or "",
        pitch_ids=pitch_ids,
        pitch_segments=segments,
        persons=booking.persons,
        services=services,
        amendments=amendments,
        warnings=warnings or [],
    )


def _load_booking(db: Session, booking_id: int) -> Booking:
    booking = db.scalar(
        select(Booking)
        .where(Booking.id == booking_id)
        .options(
            selectinload(Booking.booking_pitches).selectinload(BookingPitch.pitch),
            selectinload(Booking.persons),
            selectinload(Booking.booking_services)
            .selectinload(BookingService.service)
            .selectinload(Service.group),
            selectinload(Booking.amendments),
        )
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.get("", response_model=list[BookingRead])
def list_bookings(
    from_date: date | None = None,
    to_date: date | None = None,
    db: Session = Depends(get_db),
) -> list[BookingRead]:
    stmt = select(Booking).options(
        selectinload(Booking.booking_pitches).selectinload(BookingPitch.pitch),
        selectinload(Booking.persons),
        selectinload(Booking.booking_services)
        .selectinload(BookingService.service)
        .selectinload(Service.group),
        selectinload(Booking.amendments),
    )
    bookings = list(db.scalars(stmt).unique().all())
    if from_date is not None or to_date is not None:
        start = from_date or date.min
        end = to_date or date.max
        bookings = [b for b in bookings if b.start_date < end and start < b.end_date]
    bookings.sort(key=lambda b: b.start_date)
    return [booking_to_read(b) for b in bookings]


@router.get("/gantt", response_model=list[BookingGanttItem])
def gantt_items(
    from_date: date | None = None,
    to_date: date | None = None,
    db: Session = Depends(get_db),
) -> list[BookingGanttItem]:
    stmt = select(Booking).options(
        selectinload(Booking.booking_pitches).selectinload(BookingPitch.pitch),
    )
    bookings = list(db.scalars(stmt).unique().all())
    if from_date is not None or to_date is not None:
        start = from_date or date.min
        end = to_date or date.max
        bookings = [b for b in bookings if b.start_date < end and start < b.end_date]
    items: list[BookingGanttItem] = []
    for booking in bookings:
        for seg in booking.booking_pitches:
            items.append(
                BookingGanttItem(
                    id=booking.id,
                    group_name=booking.group_name,
                    start_date=seg.start_date,
                    end_date=seg.end_date,
                    pitch_id=seg.pitch_id,
                    pitch_name=seg.pitch.name if seg.pitch else "",
                )
            )
    items.sort(key=lambda i: (i.pitch_name, i.start_date))
    return items


@router.post("", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db)) -> BookingRead:
    _validate_persons(payload.persons, payload.start_date, payload.end_date)
    pitches = assert_pitches_bookable(db, payload.pitch_ids, payload.start_date, payload.end_date)
    booking_services = _resolve_booking_services(
        db, payload.services, payload.start_date, payload.end_date
    )
    warnings = check_services(
        db,
        payload.start_date,
        payload.end_date,
        [(bs.service_id, bs.quantity) for bs in booking_services],
    )
    booking = Booking(
        group_name=payload.group_name,
        start_date=payload.start_date,
        end_date=payload.end_date,
        notes=payload.notes or "",
        booking_pitches=[
            BookingPitch(
                pitch_id=p.id,
                start_date=payload.start_date,
                end_date=payload.end_date,
            )
            for p in pitches
        ],
        persons=[
            _person_model(p, payload.start_date, payload.end_date) for p in payload.persons
        ],
        booking_services=booking_services,
    )
    db.add(booking)
    db.commit()
    return booking_to_read(_load_booking(db, booking.id), warnings=warnings)


@router.get("/{booking_id}/invoice", response_model=InvoiceRead)
def get_invoice(booking_id: int, db: Session = Depends(get_db)) -> InvoiceRead:
    booking = load_booking_for_invoice(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return build_invoice(db, booking)


@router.get("/{booking_id}/invoice.pdf")
def get_invoice_pdf(booking_id: int, db: Session = Depends(get_db)) -> Response:
    booking = load_booking_for_invoice(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    invoice = build_invoice(db, booking)
    row = get_or_create_operator_settings(db)
    path = logo_path(row)
    logo = path if row.logo_filename and path.is_file() else None
    # #region agent log
    try:
        import json, time
        from pathlib import Path as _P
        from app.config import get_settings as _gs
        _payload = {
            "sessionId": "188c80",
            "runId": "post-fix",
            "hypothesisId": "A",
            "location": "bookings.py:get_invoice_pdf",
            "message": "pdf logo resolve",
            "data": {
                "booking_id": booking_id,
                "data_dir": str(_gs().data_dir),
                "logo_filename": row.logo_filename,
                "path": str(path),
                "exists": path.is_file() if row.logo_filename else False,
                "passed": logo is not None,
            },
            "timestamp": int(time.time() * 1000),
        }
        for _log in (
            _P(__file__).resolve().parents[4] / ".cursor" / "debug-188c80.log",
            _P(_gs().data_dir) / "pdf_debug.ndjson",
        ):
            _log.parent.mkdir(parents=True, exist_ok=True)
            with _log.open("a", encoding="utf-8") as _f:
                _f.write(json.dumps(_payload) + "\n")
    except Exception as _e:
        try:
            from app.config import get_settings as _gs2
            from pathlib import Path as _P2
            (_P2(_gs2().data_dir) / "pdf_debug_err.txt").write_text(repr(_e), encoding="utf-8")
        except Exception:
            pass
    # #endregion
    pdf = render_invoice_pdf(invoice, logo_file=logo)
    filename = f"rechnung-{booking_id}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{booking_id}/amendments", response_model=list[BookingAmendmentRead])
def list_amendments(booking_id: int, db: Session = Depends(get_db)) -> list[BookingAmendmentRead]:
    booking = _load_booking(db, booking_id)
    return [
        BookingAmendmentRead(
            id=a.id,
            effective_date=a.effective_date,
            created_at=a.created_at,
            summary=a.summary,
            diff_json=a.diff_json,
        )
        for a in booking.amendments
    ]


@router.post("/{booking_id}/amend", response_model=BookingRead)
def amend_booking(
    booking_id: int, payload: BookingAmendRequest, db: Session = Depends(get_db)
) -> BookingRead:
    booking = _load_booking(db, booking_id)
    if _booking_fully_editable(booking):
        raise HTTPException(
            status_code=409,
            detail="Vor dem Anreisetag bitte normale Bearbeitung nutzen",
        )
    if not _booking_amendable(booking) and date.today() >= booking.end_date:
        raise HTTPException(
            status_code=409,
            detail="Buchung ist beendet und kann nicht mehr angepasst werden",
        )
    # Allow amend if today is after start (running or edge: today == end-1 still running)
    if date.today() <= booking.start_date:
        raise HTTPException(status_code=409, detail="Anpassung erst nach dem Anreisetag")
    if date.today() >= booking.end_date:
        raise HTTPException(status_code=409, detail="Buchung ist beendet")

    _validate_persons(payload.persons, booking.start_date, payload.end_date)
    warnings = apply_amendment(db, booking, payload)
    db.commit()
    return booking_to_read(_load_booking(db, booking.id), warnings=warnings)


@router.get("/{booking_id}", response_model=BookingRead)
def get_booking(booking_id: int, db: Session = Depends(get_db)) -> BookingRead:
    return booking_to_read(_load_booking(db, booking_id))


@router.patch("/{booking_id}", response_model=BookingRead)
def update_booking(
    booking_id: int, payload: BookingUpdate, db: Session = Depends(get_db)
) -> BookingRead:
    booking = _load_booking(db, booking_id)
    data = payload.model_dump(exclude_unset=True)

    if set(data.keys()) <= {"notes"}:
        if "notes" in data:
            booking.notes = data["notes"] or ""
        db.commit()
        return booking_to_read(_load_booking(db, booking.id))

    if not _booking_fully_editable(booking):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Buchung kann nach dem Anreisetag nicht mehr vollständig bearbeitet werden",
        )

    start = data.get("start_date", booking.start_date)
    end = data.get("end_date", booking.end_date)
    if start >= end:
        raise HTTPException(status_code=422, detail="start_date must be before end_date")

    pitch_ids = data.get(
        "pitch_ids",
        list(dict.fromkeys(s.pitch_id for s in booking.booking_pitches)),
    )
    pitches = assert_pitches_bookable(
        db, pitch_ids, start, end, exclude_booking_id=booking.id
    )

    if "group_name" in data:
        booking.group_name = data["group_name"]
    if "notes" in data:
        booking.notes = data["notes"] or ""
    booking.start_date = start
    booking.end_date = end
    booking.booking_pitches.clear()
    for p in pitches:
        booking.booking_pitches.append(
            BookingPitch(pitch_id=p.id, start_date=start, end_date=end)
        )

    if "persons" in data and payload.persons is not None:
        _validate_persons(payload.persons, start, end)
        booking.persons.clear()
        for p in payload.persons:
            booking.persons.append(_person_model(p, start, end))
    else:
        for person in booking.persons:
            if person.start_date < start or person.end_date > end or person.start_date >= person.end_date:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Person '{person.name}': Zeitraum muss innerhalb "
                        f"der Buchung ({start}–{end}) liegen"
                    ),
                )

    warnings: list[str] = []
    if "services" in data and payload.services is not None:
        booking_services = _resolve_booking_services(db, payload.services, start, end)
        warnings = check_services(
            db,
            start,
            end,
            [(bs.service_id, bs.quantity) for bs in booking_services],
            exclude_booking_id=booking.id,
        )
        booking.booking_services.clear()
        for bs in booking_services:
            booking.booking_services.append(bs)
    else:
        for bs in booking.booking_services:
            bs.start_date = start
            bs.end_date = end
        warnings = check_services(
            db,
            start,
            end,
            [(bs.service_id, bs.quantity) for bs in booking.booking_services],
            exclude_booking_id=booking.id,
        )

    db.commit()
    return booking_to_read(_load_booking(db, booking.id), warnings=warnings)


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_booking(booking_id: int, db: Session = Depends(get_db)) -> None:
    booking = _load_booking(db, booking_id)
    db.delete(booking)
    db.commit()
