from __future__ import annotations

import json
from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Booking, BookingAmendment, BookingPitch, BookingService, Person, Pitch, Service
from app.schemas import BookingAmendRequest, PersonCreate
from app.services.availability import assert_pitches_bookable, intervals_overlap, pitch_ids_active_from
from app.services.service_availability import check_services, service_qty_from


def _person_key(p: Person | PersonCreate) -> tuple[str, date, str]:
    return (p.name.strip().lower(), p.birth_date, p.nationality.upper())


def apply_amendment(db: Session, booking: Booking, payload: BookingAmendRequest) -> list[str]:
    effective = payload.effective_date
    new_end = payload.end_date
    old_end = booking.end_date

    if not (booking.start_date <= effective < booking.end_date):
        raise HTTPException(
            status_code=422,
            detail="Wirkdatum muss innerhalb der Buchung [Anreise, Abreise) liegen",
        )
    if effective >= new_end:
        raise HTTPException(status_code=422, detail="Wirkdatum muss vor der Abreise liegen")
    if new_end <= booking.start_date:
        raise HTTPException(status_code=422, detail="Abreise muss nach der Anreise liegen")

    desired_pitches = list(dict.fromkeys(payload.pitch_ids))
    if not desired_pitches:
        raise HTTPException(status_code=422, detail="Mindestens ein Zeltplatz ab Wirkdatum erforderlich")

    assert_pitches_bookable(
        db,
        desired_pitches,
        effective,
        new_end,
        exclude_booking_id=booking.id,
    )

    desired_services = {s.service_id: s.quantity for s in payload.services if s.quantity > 0}
    warnings = check_services(
        db,
        effective,
        new_end,
        list(desired_services.items()),
        exclude_booking_id=booking.id,
    )

    before_pitches = pitch_ids_active_from(booking, effective)
    before_services = service_qty_from(booking, effective)
    before_persons = [
        {
            "name": p.name,
            "birth_date": p.birth_date.isoformat(),
            "nationality": p.nationality,
            "start_date": p.start_date.isoformat(),
            "end_date": p.end_date.isoformat(),
        }
        for p in booking.persons
        if p.end_date > effective
    ]

    # --- pitches: close removed, open added, clip/extend ---
    for seg in list(booking.booking_pitches):
        if seg.end_date <= effective:
            continue
        if seg.pitch_id not in desired_pitches:
            if seg.start_date >= effective:
                booking.booking_pitches.remove(seg)
            else:
                seg.end_date = effective
            continue
        # desired pitch: ensure covers [effective, new_end)
        if seg.start_date <= effective < seg.end_date:
            seg.end_date = new_end
        elif seg.start_date > effective:
            if seg.end_date == old_end:
                seg.end_date = new_end
            elif seg.end_date > new_end:
                seg.end_date = new_end

    for pitch_id in desired_pitches:
        covers = any(
            s.pitch_id == pitch_id and intervals_overlap(effective, new_end, s.start_date, s.end_date)
            for s in booking.booking_pitches
        )
        if not covers:
            booking.booking_pitches.append(
                BookingPitch(pitch_id=pitch_id, start_date=effective, end_date=new_end)
            )

    for seg in list(booking.booking_pitches):
        if seg.end_date > new_end:
            seg.end_date = new_end
        if seg.start_date >= seg.end_date:
            booking.booking_pitches.remove(seg)

    # --- services ---
    handled: set[int] = set()
    for row in list(booking.booking_services):
        if row.end_date <= effective:
            continue
        desired_qty = desired_services.get(row.service_id)
        if desired_qty is None:
            if row.start_date >= effective:
                booking.booking_services.remove(row)
            else:
                row.end_date = effective
            continue
        if row.start_date <= effective < row.end_date:
            handled.add(row.service_id)
            if row.quantity != desired_qty:
                row.end_date = effective
                booking.booking_services.append(
                    BookingService(
                        service_id=row.service_id,
                        quantity=desired_qty,
                        start_date=effective,
                        end_date=new_end,
                    )
                )
            else:
                row.end_date = new_end
        elif row.start_date > effective:
            booking.booking_services.remove(row)

    for service_id, qty in desired_services.items():
        if service_id in handled:
            continue
        covers = any(
            r.service_id == service_id and r.start_date <= effective < r.end_date
            for r in booking.booking_services
        )
        if covers:
            continue
        if not db.get(Service, service_id):
            raise HTTPException(status_code=404, detail=f"Service {service_id} not found")
        booking.booking_services.append(
            BookingService(
                service_id=service_id,
                quantity=qty,
                start_date=effective,
                end_date=new_end,
            )
        )

    for row in list(booking.booking_services):
        if row.end_date > new_end:
            row.end_date = new_end
        if row.start_date >= row.end_date:
            booking.booking_services.remove(row)

    # --- persons ---
    payload_keys = {_person_key(p) for p in payload.persons}
    for person in list(booking.persons):
        if person.end_date <= effective:
            continue
        key = _person_key(person)
        if key not in payload_keys:
            if person.start_date >= effective:
                booking.persons.remove(person)
            else:
                person.end_date = effective
        else:
            match = next(p for p in payload.persons if _person_key(p) == key)
            end = match.end_date or new_end
            if end > new_end:
                end = new_end
            if person.end_date == old_end or person.end_date > effective:
                person.end_date = end

    existing_active = {_person_key(p) for p in booking.persons if p.end_date > effective}
    for p in payload.persons:
        key = _person_key(p)
        if key in existing_active:
            continue
        start = max(p.start_date or effective, effective)
        end = min(p.end_date or new_end, new_end)
        if start >= end:
            raise HTTPException(status_code=422, detail=f"Person '{p.name}': ungültiger Zeitraum")
        booking.persons.append(
            Person(
                name=p.name,
                birth_date=p.birth_date,
                nationality=p.nationality,
                start_date=start,
                end_date=end,
            )
        )

    for person in booking.persons:
        if person.end_date > new_end:
            person.end_date = new_end

    booking.end_date = new_end

    pitch_name_by_id: dict[int, str] = {}
    needed_pitch_ids = set(before_pitches) | set(desired_pitches)
    if needed_pitch_ids:
        for p in db.scalars(select(Pitch).where(Pitch.id.in_(needed_pitch_ids))).all():
            pitch_name_by_id[p.id] = p.name

    service_name_by_id: dict[int, str] = {}
    needed_svc = set(before_services) | set(desired_services)
    if needed_svc:
        for s in db.scalars(select(Service).where(Service.id.in_(needed_svc))).all():
            service_name_by_id[s.id] = s.name

    change_lines: list[str] = []
    for pid in sorted(set(before_pitches) - set(desired_pitches)):
        change_lines.append(f'− Platz "{pitch_name_by_id.get(pid, pid)}"')
    for pid in sorted(set(desired_pitches) - set(before_pitches)):
        change_lines.append(f'+ Platz "{pitch_name_by_id.get(pid, pid)}"')

    before_person_keys = {
        (p["name"].strip().lower(), p["birth_date"], p["nationality"].upper()): p["name"]
        for p in before_persons
    }
    after_active = [p for p in booking.persons if p.end_date > effective]
    after_person_keys = {
        (p.name.strip().lower(), p.birth_date.isoformat(), p.nationality.upper()): p.name
        for p in after_active
    }
    for key, name in before_person_keys.items():
        if key not in after_person_keys:
            change_lines.append(f'− Person "{name}"')
    for key, name in after_person_keys.items():
        if key not in before_person_keys:
            change_lines.append(f'+ Person "{name}"')

    all_svc_ids = set(before_services) | set(desired_services)
    for sid in sorted(all_svc_ids):
        old_q = before_services.get(sid, 0)
        new_q = desired_services.get(sid, 0)
        name = service_name_by_id.get(sid, str(sid))
        if old_q == new_q:
            continue
        if old_q == 0 and new_q > 0:
            change_lines.append(f"+ {new_q}x {name}")
        elif new_q == 0 and old_q > 0:
            change_lines.append(f"− {old_q}x {name}")
        else:
            change_lines.append(f"~ {name}: {old_q}x → {new_q}x")

    if old_end != new_end:
        change_lines.append(f"Abreise {old_end.isoformat()} → {new_end.isoformat()}")

    if not change_lines:
        change_lines.append("Keine Netto-Änderung")

    summary = " · ".join(change_lines)
    if len(summary) > 500:
        summary = summary[:497] + "…"

    diff = {
        "effective_date": effective.isoformat(),
        "end_date": {"from": old_end.isoformat(), "to": new_end.isoformat()},
        "pitches": {"from": before_pitches, "to": desired_pitches},
        "services": {
            "from": {str(k): v for k, v in before_services.items()},
            "to": {str(k): v for k, v in desired_services.items()},
        },
        "persons_before": before_persons,
        "changes": change_lines,
    }
    booking.amendments.append(
        BookingAmendment(
            effective_date=effective,
            summary=summary,
            diff_json=json.dumps(diff, ensure_ascii=False),
        )
    )
    return warnings
