from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.user import get_current_user_mobile
from app.api.host_policy import require_host_policy
from app.core.errors import AppError
from app.db.session import get_db
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.user import User
from app.schemas.common import Audience, PrincipalType
from app.schemas.order.order import OrderCreate, OrderItemOut, OrderOut
from app.services import order_service

router = APIRouter(
    prefix="/user/orders",
    tags=["user-orders"],
    dependencies=[Depends(require_host_policy(principal=PrincipalType.user, audience=Audience.mobile))],
)


def _order_out(order: Order) -> OrderOut:
    return OrderOut(
        id=order.id,
        store_id=order.store_id,
        user_id=order.user_id,
        status=order.status,
        channel=order.channel,
        subtotal=order.subtotal,
        tax=order.tax,
        total=order.total,
        notes=order.notes,
        created_at=order.created_at,
    )


def _order_item_out(item: OrderItem) -> OrderItemOut:
    return OrderItemOut(
        id=item.id,
        order_id=item.order_id,
        menu_item_id=item.menu_item_id,
        quantity=item.quantity,
        price_snapshot=item.price_snapshot,
    )


@router.get("", response_model=list[OrderOut])
def list_orders(
    current_user: User = Depends(get_current_user_mobile),
    db: Session = Depends(get_db),
) -> list[OrderOut]:
    orders = db.execute(
        select(Order).where(Order.user_id == current_user.id).order_by(Order.created_at.desc())
    ).scalars().all()
    return [_order_out(order) for order in orders]


@router.post("", response_model=OrderOut)
def create_order(
    payload: OrderCreate,
    current_user: User = Depends(get_current_user_mobile),
    db: Session = Depends(get_db),
) -> OrderOut:
    payload = payload.model_copy(update={"user_id": current_user.id})
    order = order_service.create_draft_order(db, payload=payload)
    db.commit()
    db.refresh(order)
    return _order_out(order)


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user_mobile),
    db: Session = Depends(get_db),
) -> OrderOut:
    order = db.execute(
        select(Order).where(Order.user_id == current_user.id).where(Order.id == order_id)
    ).scalar_one_or_none()
    if order is None:
        raise AppError(status_code=404, code="order_not_found", detail="Order not found")
    return _order_out(order)


@router.get("/{order_id}/items", response_model=list[OrderItemOut])
def list_order_items(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user_mobile),
    db: Session = Depends(get_db),
) -> list[dict]:
    order = db.execute(
        select(Order).where(Order.user_id == current_user.id).where(Order.id == order_id)
    ).scalar_one_or_none()
    if order is None:
        raise AppError(status_code=404, code="order_not_found", detail="Order not found")

    items = db.execute(select(OrderItem).where(OrderItem.order_id == order.id)).scalars().all()
    return [_order_item_out(item) for item in items]
