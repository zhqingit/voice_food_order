from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.store import get_current_store_web
from app.api.host_policy import require_host_policy
from app.core.errors import AppError
from app.db.session import get_db
from app.models.menu_item import MenuItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.store import Store
from app.models.user import User
from app.models.voice_session import VoiceSession
from app.schemas.common import Audience, PrincipalType
from app.schemas.order.order import OrderItemOut, OrderOut, OrderStatusUpdate

router = APIRouter(
    prefix="/store/orders",
    tags=["store-orders"],
    dependencies=[Depends(require_host_policy(principal=PrincipalType.store, audience=Audience.web))],
)


def _order_out(order: Order, db: Session) -> OrderOut:
    user_email: str | None = None
    if order.user_id is not None:
        user = db.get(User, order.user_id)
        if user is not None:
            user_email = user.email
    return OrderOut(
        id=order.id,
        short_code=order.short_code,
        code_day=order.code_day,
        store_id=order.store_id,
        user_id=order.user_id,
        status=order.status,
        payment_status=order.payment_status,
        channel=order.channel,
        subtotal=order.subtotal,
        tax=order.tax,
        total=order.total,
        customer_name=order.customer_name,
        user_email=user_email,
        notes=order.notes,
        fulfillment_type=order.fulfillment_type,
        delivery_address=order.delivery_address,
        created_at=order.created_at,
    )


def _order_item_out(item: OrderItem, db: Session) -> OrderItemOut:
    menu_item = db.get(MenuItem, item.menu_item_id)
    return OrderItemOut(
        id=item.id,
        order_id=item.order_id,
        menu_item_id=item.menu_item_id,
        name=menu_item.name if menu_item else None,
        quantity=item.quantity,
        price_snapshot=item.price_snapshot,
        note=item.note,
        variant_name=item.variant_name,
    )


@router.get("", response_model=list[OrderOut])
def list_orders(
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> list[OrderOut]:
    orders = db.execute(
        select(Order).where(Order.store_id == current_store.id).order_by(Order.created_at.desc())
    ).scalars().all()
    return [_order_out(order, db) for order in orders]


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: uuid.UUID,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> OrderOut:
    order = db.execute(
        select(Order).where(Order.store_id == current_store.id).where(Order.id == order_id)
    ).scalar_one_or_none()
    if order is None:
        raise AppError(status_code=404, code="order_not_found", detail="Order not found")
    return _order_out(order, db)


@router.patch("/{order_id}", response_model=OrderOut)
def update_order_status(
    order_id: uuid.UUID,
    payload: OrderStatusUpdate,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> OrderOut:
    order = db.execute(
        select(Order).where(Order.store_id == current_store.id).where(Order.id == order_id)
    ).scalar_one_or_none()
    if order is None:
        raise AppError(status_code=404, code="order_not_found", detail="Order not found")

    order.status = payload.status
    db.commit()
    db.refresh(order)
    return _order_out(order, db)


@router.get("/{order_id}/items", response_model=list[OrderItemOut])
def list_order_items(
    order_id: uuid.UUID,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> list[dict]:
    order = db.execute(
        select(Order).where(Order.store_id == current_store.id).where(Order.id == order_id)
    ).scalar_one_or_none()
    if order is None:
        raise AppError(status_code=404, code="order_not_found", detail="Order not found")

    items = db.execute(select(OrderItem).where(OrderItem.order_id == order.id)).scalars().all()
    return [_order_item_out(item, db) for item in items]


@router.get("/{order_id}/usage")
def get_order_usage(
    order_id: uuid.UUID,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> dict:
    """Get token usage and cost for the voice session that created this order."""
    order = db.execute(
        select(Order).where(Order.store_id == current_store.id).where(Order.id == order_id)
    ).scalar_one_or_none()
    if order is None:
        raise AppError(status_code=404, code="order_not_found", detail="Order not found")

    vs = db.execute(
        select(VoiceSession).where(VoiceSession.order_id == order_id)
    ).scalar_one_or_none()

    if vs is None:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "llm_cost": "0"}

    return {
        "prompt_tokens": vs.prompt_tokens,
        "completion_tokens": vs.completion_tokens,
        "total_tokens": vs.total_tokens,
        "llm_cost": str(vs.llm_cost),
    }
