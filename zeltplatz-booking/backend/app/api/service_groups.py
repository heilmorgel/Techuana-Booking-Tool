from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import ServiceGroup
from app.schemas import ServiceGroupCreate, ServiceGroupRead, ServiceGroupUpdate

router = APIRouter(prefix="/service-groups", tags=["service-groups"])


def _to_read(group: ServiceGroup, service_count: int | None = None) -> ServiceGroupRead:
    count = service_count if service_count is not None else len(group.services)
    return ServiceGroupRead(id=group.id, name=group.name, service_count=count)


@router.get("", response_model=list[ServiceGroupRead])
def list_groups(db: Session = Depends(get_db)) -> list[ServiceGroupRead]:
    groups = list(
        db.scalars(select(ServiceGroup).options(selectinload(ServiceGroup.services)).order_by(ServiceGroup.name)).all()
    )
    return [_to_read(g) for g in groups]


@router.post("", response_model=ServiceGroupRead, status_code=status.HTTP_201_CREATED)
def create_group(payload: ServiceGroupCreate, db: Session = Depends(get_db)) -> ServiceGroupRead:
    existing = db.scalar(select(ServiceGroup).where(ServiceGroup.name == payload.name))
    if existing:
        raise HTTPException(status_code=409, detail="Service group name already exists")
    group = ServiceGroup(name=payload.name)
    db.add(group)
    db.commit()
    db.refresh(group)
    return _to_read(group, service_count=0)


@router.patch("/{group_id}", response_model=ServiceGroupRead)
def update_group(group_id: int, payload: ServiceGroupUpdate, db: Session = Depends(get_db)) -> ServiceGroupRead:
    group = db.scalar(
        select(ServiceGroup).where(ServiceGroup.id == group_id).options(selectinload(ServiceGroup.services))
    )
    if not group:
        raise HTTPException(status_code=404, detail="Service group not found")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        clash = db.scalar(
            select(ServiceGroup).where(ServiceGroup.name == data["name"], ServiceGroup.id != group_id)
        )
        if clash:
            raise HTTPException(status_code=409, detail="Service group name already exists")
        group.name = data["name"]
    db.commit()
    db.refresh(group)
    return _to_read(group)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(group_id: int, db: Session = Depends(get_db)) -> None:
    group = db.scalar(
        select(ServiceGroup).where(ServiceGroup.id == group_id).options(selectinload(ServiceGroup.services))
    )
    if not group:
        raise HTTPException(status_code=404, detail="Service group not found")
    if group.services:
        raise HTTPException(status_code=409, detail="Service group still has services and cannot be deleted")
    db.delete(group)
    db.commit()
