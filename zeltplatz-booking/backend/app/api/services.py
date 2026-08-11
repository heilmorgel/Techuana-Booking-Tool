from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import BookingService, Service, ServiceGroup
from app.schemas import (
    ServiceAvailabilityRead,
    ServiceCreate,
    ServiceRead,
    ServiceUpdate,
)
from app.services.service_availability import service_availability_rows

router = APIRouter(prefix="/services", tags=["services"])


def _to_read(service: Service) -> ServiceRead:
    return ServiceRead(
        id=service.id,
        name=service.name,
        group_id=service.group_id,
        group_name=service.group.name if service.group else "",
        available_quantity=service.available_quantity,
        daily_price=float(service.daily_price or 0),
    )


@router.get("/availability", response_model=list[ServiceAvailabilityRead])
def get_availability(
    start: date,
    end: date,
    exclude_booking_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[ServiceAvailabilityRead]:
    if start >= end:
        raise HTTPException(status_code=422, detail="start must be before end")
    rows = service_availability_rows(db, start, end, exclude_booking_id=exclude_booking_id)
    return [ServiceAvailabilityRead(**row) for row in rows]


@router.get("", response_model=list[ServiceRead])
def list_services(group_id: int | None = None, db: Session = Depends(get_db)) -> list[ServiceRead]:
    stmt = select(Service).options(selectinload(Service.group)).order_by(Service.name)
    if group_id is not None:
        stmt = stmt.where(Service.group_id == group_id)
    return [_to_read(s) for s in db.scalars(stmt).all()]


@router.post("", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
def create_service(payload: ServiceCreate, db: Session = Depends(get_db)) -> ServiceRead:
    group = db.get(ServiceGroup, payload.group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Service group not found")
    clash = db.scalar(
        select(Service).where(Service.group_id == payload.group_id, Service.name == payload.name)
    )
    if clash:
        raise HTTPException(status_code=409, detail="Service name already exists in this group")
    service = Service(
        name=payload.name,
        group_id=payload.group_id,
        available_quantity=payload.available_quantity,
        daily_price=payload.daily_price,
    )
    db.add(service)
    db.commit()
    service = db.scalar(
        select(Service).where(Service.id == service.id).options(selectinload(Service.group))
    )
    assert service is not None
    return _to_read(service)


@router.patch("/{service_id}", response_model=ServiceRead)
def update_service(service_id: int, payload: ServiceUpdate, db: Session = Depends(get_db)) -> ServiceRead:
    service = db.scalar(
        select(Service).where(Service.id == service_id).options(selectinload(Service.group))
    )
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    data = payload.model_dump(exclude_unset=True)
    new_group_id = data.get("group_id", service.group_id)
    new_name = data.get("name", service.name)
    if "group_id" in data:
        group = db.get(ServiceGroup, data["group_id"])
        if not group:
            raise HTTPException(status_code=404, detail="Service group not found")
    if new_name != service.name or new_group_id != service.group_id:
        clash = db.scalar(
            select(Service).where(
                Service.group_id == new_group_id,
                Service.name == new_name,
                Service.id != service_id,
            )
        )
        if clash:
            raise HTTPException(status_code=409, detail="Service name already exists in this group")
    for key, value in data.items():
        setattr(service, key, value)
    db.commit()
    service = db.scalar(
        select(Service).where(Service.id == service_id).options(selectinload(Service.group))
    )
    assert service is not None
    return _to_read(service)


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(service_id: int, db: Session = Depends(get_db)) -> None:
    service = db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    linked = db.scalar(select(BookingService).where(BookingService.service_id == service_id).limit(1))
    if linked:
        raise HTTPException(status_code=409, detail="Service is used in bookings and cannot be deleted")
    db.delete(service)
    db.commit()
