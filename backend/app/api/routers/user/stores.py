from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.host_policy import require_host_policy
from app.core.errors import AppError
from app.db.session import get_db
from app.models.store import Store
from app.models.store_hours import StoreHours
from app.schemas.common import Audience, PrincipalType
from app.schemas.menu.menu import MenuItemOut
from app.schemas.store.hours import DayHours
from app.schemas.store.store import StorePublicOut
from app.services import delivery_service, menu_service

router = APIRouter(
    prefix="/user/stores",
    tags=["user-stores"],
    dependencies=[Depends(require_host_policy(principal=PrincipalType.user, audience=Audience.mobile))],
)


def _hours_for_store(db: Session, store_id: uuid.UUID) -> list[DayHours]:
    rows = (
        db.execute(
            select(StoreHours)
            .where(StoreHours.store_id == store_id)
            .order_by(StoreHours.day_of_week)
        )
        .scalars()
        .all()
    )
    return [
        DayHours(
            day_of_week=r.day_of_week,
            open_time=r.open_time.strftime("%H:%M"),
            close_time=r.close_time.strftime("%H:%M"),
            is_closed=r.is_closed,
        )
        for r in rows
    ]


def _store_public_out(store: Store, hours: list[DayHours]) -> StorePublicOut:
    return StorePublicOut(
        id=store.id,
        name=store.name,
        phone=store.phone,
        address_line1=store.address_line1,
        city=store.city,
        state=store.state,
        country=store.country,
        timezone=store.timezone,
        allow_pickup=store.allow_pickup,
        allow_delivery=store.allow_delivery,
        min_order_amount=store.min_order_amount,
        logo_url=store.logo_url,
        hours=hours,
    )


@router.get("", response_model=list[StorePublicOut])
def list_stores(db: Session = Depends(get_db)) -> list[StorePublicOut]:
    """List all active stores, sorted by creation date descending."""
    stores = (
        db.execute(select(Store).where(Store.is_active == True, Store.is_approved == True, Store.is_published == True).order_by(Store.created_at.desc()))  # noqa: E712
        .scalars()
        .all()
    )
    return [_store_public_out(store, _hours_for_store(db, store.id)) for store in stores]


@router.get("/{store_id}", response_model=StorePublicOut)
def get_store(store_id: uuid.UUID, db: Session = Depends(get_db)) -> StorePublicOut:
    """Get a single store by ID. Returns 404 if not found, or 410 if unpublished."""
    store = db.get(Store, store_id)
    if store is None or not store.is_active or not store.is_approved:
        raise AppError(status_code=404, code="store_not_found", detail="Store not found")
    if not store.is_published:
        raise AppError(status_code=410, code="store_unpublished", detail="This store is no longer available")
    return _store_public_out(store, _hours_for_store(db, store.id))


@router.get("/{store_id}/menu", response_model=list[MenuItemOut])
def get_store_menu(store_id: uuid.UUID, db: Session = Depends(get_db)) -> list[MenuItemOut]:
    """Return the active menu items for a store (public, no auth required)."""
    store = db.get(Store, store_id)
    if store is None or not store.is_active or not store.is_approved or not store.is_published:
        raise AppError(status_code=404, code="store_not_found", detail="Store not found")
    menu = menu_service.get_menu_by_version(db, store_id=store.id, version=None)
    if menu is None:
        return []
    items = menu_service.list_menu_items(db, menu_id=menu.id)
    return [MenuItemOut.model_validate(item, from_attributes=True) for item in items]


class DeliveryRangeCheckIn(BaseModel):
    address: str = Field(min_length=1, max_length=512)


class DeliveryRangeCheckOut(BaseModel):
    in_range: bool
    distance_km: float | None = None
    max_km: float | None = None
    reason: str


@router.post("/{store_id}/delivery/check-range", response_model=DeliveryRangeCheckOut)
def check_delivery_range(
    store_id: uuid.UUID,
    payload: DeliveryRangeCheckIn,
    db: Session = Depends(get_db),
) -> DeliveryRangeCheckOut:
    """Pre-check whether an address can be delivered to. Lets the user portal
    show an out-of-range hint before the customer builds a cart."""
    store = db.get(Store, store_id)
    if store is None or not store.is_active or not store.is_approved or not store.is_published:
        raise AppError(status_code=404, code="store_not_found", detail="Store not found")
    in_range, distance_km, reason = delivery_service.is_within_delivery_range(store, payload.address)
    return DeliveryRangeCheckOut(
        in_range=in_range,
        distance_km=round(distance_km, 2) if distance_km is not None else None,
        max_km=float(store.delivery_radius_km) if store.delivery_radius_km is not None else None,
        reason=reason,
    )
