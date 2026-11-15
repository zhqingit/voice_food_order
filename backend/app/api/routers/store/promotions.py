"""The store's own promotions (store-funded discounts, applied automatically)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps.store import get_current_store_web
from app.api.host_policy import require_host_policy
from app.core.errors import AppError
from app.db.session import get_db
from app.models.order import Order
from app.models.promotion import Promotion
from app.models.store import Store
from app.schemas.common import Audience, PrincipalType
from app.schemas.store.promotions import PromotionCreate, PromotionOut, PromotionUpdate

router = APIRouter(
    prefix="/store/promotions",
    tags=["store-promotions"],
    dependencies=[Depends(require_host_policy(principal=PrincipalType.store, audience=Audience.web))],
)


def _orders_count(db: Session, promo_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not promo_ids:
        return {}
    rows = db.execute(
        select(Order.promotion_id, func.count())
        .where(Order.promotion_id.in_(promo_ids), Order.status != "draft")
        .group_by(Order.promotion_id)
    ).all()
    return dict(rows)


def _out(p: Promotion, orders_count: int) -> PromotionOut:
    return PromotionOut(
        id=p.id, name=p.name, kind=p.kind, value=p.value, min_subtotal=p.min_subtotal, channels=p.channels,
        starts_on=p.starts_on, ends_on=p.ends_on, is_active=p.is_active, orders_count=orders_count, created_at=p.created_at,
    )


def _get(db: Session, store: Store, promo_id: uuid.UUID) -> Promotion:
    promo = db.get(Promotion, promo_id)
    if promo is None or promo.store_id != store.id:
        raise AppError(status_code=404, code="promotion_not_found", detail="Promotion not found")
    return promo


@router.get("", response_model=list[PromotionOut])
def list_promotions(
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> list[PromotionOut]:
    rows = db.execute(
        select(Promotion).where(Promotion.store_id == current_store.id).order_by(Promotion.created_at.desc())
    ).scalars().all()
    counts = _orders_count(db, [p.id for p in rows])
    return [_out(p, counts.get(p.id, 0)) for p in rows]


@router.post("", response_model=PromotionOut, status_code=201)
def create_promotion(
    payload: PromotionCreate,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> PromotionOut:
    promo = Promotion(store_id=current_store.id, **payload.model_dump())
    promo.name = promo.name.strip()
    db.add(promo)
    db.commit()
    return _out(promo, 0)


@router.patch("/{promo_id}", response_model=PromotionOut)
def update_promotion(
    promo_id: uuid.UUID,
    payload: PromotionUpdate,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> PromotionOut:
    promo = _get(db, current_store, promo_id)
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] is not None:
        promo.name = changes["name"].strip()
    if changes.get("is_active") is not None:
        promo.is_active = changes["is_active"]
    if "starts_on" in changes:
        promo.starts_on = changes["starts_on"]
    if "ends_on" in changes:
        promo.ends_on = changes["ends_on"]
    if promo.starts_on and promo.ends_on and promo.ends_on < promo.starts_on:
        raise AppError(status_code=422, code="invalid_dates", detail="The end date is before the start date.")
    db.commit()
    return _out(promo, _orders_count(db, [promo.id]).get(promo.id, 0))


@router.delete("/{promo_id}", status_code=204)
def delete_promotion(
    promo_id: uuid.UUID,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> Response:
    promo = _get(db, current_store, promo_id)
    used = db.execute(select(Order.id).where(Order.promotion_id == promo.id).limit(1)).first()
    if used is not None:
        raise AppError(
            status_code=409, code="promotion_in_use", detail="Orders used this promotion; turn it off instead of deleting it."
        )
    db.delete(promo)
    db.commit()
    return Response(status_code=204)
