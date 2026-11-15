"""VoxEats-funded promotions (platform promotions), for online payments only."""
from __future__ import annotations

import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps.admin import get_current_admin
from app.api.host_policy import require_host_policy
from app.core.config import settings
from app.core.errors import AppError
from app.db.session import get_db
from app.models.admin import Admin
from app.models.order import Order
from app.models.promotion import Promotion
from app.schemas.common import Audience, PrincipalType
from app.schemas.store.promotions import PlatformPromotionCreate, PlatformPromotionOut, PlatformPromotionUpdate
from app.services import platform_promotions

router = APIRouter(
    prefix="/admin/promotions",
    tags=["admin-promotions"],
    dependencies=[Depends(require_host_policy(principal=PrincipalType.admin, audience=Audience.admin))],
)


def _out(db: Session, p: Promotion) -> PlatformPromotionOut:
    today = datetime.now(ZoneInfo(settings.store_default_timezone)).date()
    orders = db.execute(
        select(func.count()).select_from(Order).where(Order.platform_promotion_id == p.id, Order.platform_discount > 0)
    ).scalar_one()
    return PlatformPromotionOut(
        id=p.id, name=p.name, kind=p.kind, value=p.value, min_subtotal=p.min_subtotal, channels=p.channels,
        starts_on=p.starts_on, ends_on=p.ends_on, is_active=p.is_active, orders_count=orders, created_at=p.created_at,
        first_order_only=p.first_order_only, per_user_limit=p.per_user_limit, monthly_budget=p.monthly_budget,
        spent_this_month=platform_promotions.spent_this_month(db, p, today),
    )


def _get(db: Session, promo_id: uuid.UUID) -> Promotion:
    promo = db.get(Promotion, promo_id)
    if promo is None or promo.store_id is not None:
        raise AppError(status_code=404, code="promotion_not_found", detail="Promotion not found")
    return promo


@router.get("", response_model=list[PlatformPromotionOut])
def list_promotions(_: Admin = Depends(get_current_admin), db: Session = Depends(get_db)) -> list[PlatformPromotionOut]:
    rows = db.execute(
        select(Promotion).where(Promotion.store_id.is_(None)).order_by(Promotion.created_at.desc())
    ).scalars().all()
    return [_out(db, p) for p in rows]


@router.post("", response_model=PlatformPromotionOut, status_code=201)
def create_promotion(
    payload: PlatformPromotionCreate,
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> PlatformPromotionOut:
    promo = Promotion(store_id=None, **payload.model_dump())
    promo.name = promo.name.strip()
    db.add(promo)
    db.commit()
    return _out(db, promo)


@router.patch("/{promo_id}", response_model=PlatformPromotionOut)
def update_promotion(
    promo_id: uuid.UUID,
    payload: PlatformPromotionUpdate,
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> PlatformPromotionOut:
    promo = _get(db, promo_id)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("name"):
        promo.name = changes["name"].strip()
    for field in ("is_active", "first_order_only"):
        if changes.get(field) is not None:
            setattr(promo, field, changes[field])
    # Dates and limits may be cleared with null.
    for field in ("starts_on", "ends_on", "per_user_limit", "monthly_budget"):
        if field in changes:
            setattr(promo, field, changes[field])
    if promo.starts_on and promo.ends_on and promo.ends_on < promo.starts_on:
        raise AppError(status_code=422, code="invalid_dates", detail="The end date is before the start date.")
    db.commit()
    return _out(db, promo)


@router.delete("/{promo_id}", status_code=204)
def delete_promotion(
    promo_id: uuid.UUID,
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Response:
    promo = _get(db, promo_id)
    if db.execute(select(Order.id).where(Order.platform_promotion_id == promo.id).limit(1)).first() is not None:
        raise AppError(status_code=409, code="promotion_in_use", detail="Orders used this promotion; turn it off instead.")
    db.delete(promo)
    db.commit()
    return Response(status_code=204)
