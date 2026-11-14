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
from app.models.order_event import OrderEvent
from app.models.order_item import OrderItem
from app.models.store import Store
from app.models.user import User
from app.models.voice_session import VoiceSession
from app.schemas.common import Audience, PrincipalType
from app.schemas.order.order import (
    OrderEventOut,
    OrderItemOut,
    OrderOut,
    OrderStatusUpdate,
    StoreOrderItemAdd,
    StoreOrderItemUpdate,
)
from app.services import store_order_edit_service

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
        customer_phone=order.customer_phone,
        user_email=user_email,
        notes=order.notes,
        fulfillment_type=order.fulfillment_type,
        delivery_address=order.delivery_address,
        created_at=order.created_at,
    )


def _get_store_order(db: Session, store: Store, order_id: uuid.UUID, *, lock: bool = False) -> Order:
    query = select(Order).where(Order.store_id == store.id).where(Order.id == order_id)
    if lock:
        query = query.with_for_update()
    order = db.execute(query).scalar_one_or_none()
    if order is None:
        raise AppError(status_code=404, code="order_not_found", detail="Order not found")
    return order


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
    order = _get_store_order(db, current_store, order_id, lock=True)
    store_order_edit_service.set_status(db, order, payload.status)
    db.commit()
    db.refresh(order)
    return _order_out(order, db)


@router.post("/{order_id}/items", response_model=OrderOut)
def add_order_item(
    order_id: uuid.UUID,
    payload: StoreOrderItemAdd,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> OrderOut:
    """Staff add an item to a placed order; totals are recalculated."""
    order = _get_store_order(db, current_store, order_id, lock=True)
    store_order_edit_service.add_item(
        db,
        order,
        menu_item_id=payload.menu_item_id,
        variant_id=payload.variant_id,
        quantity=payload.quantity,
        note=payload.note,
    )
    db.commit()
    db.refresh(order)
    return _order_out(order, db)


@router.patch("/{order_id}/items/{item_id}", response_model=OrderOut)
def update_order_item(
    order_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: StoreOrderItemUpdate,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> OrderOut:
    """Staff change an item's quantity or note."""
    order = _get_store_order(db, current_store, order_id, lock=True)
    store_order_edit_service.update_item(
        db,
        order,
        item_id,
        quantity=payload.quantity,
        note=payload.note,
        note_set="note" in payload.model_fields_set,
    )
    db.commit()
    db.refresh(order)
    return _order_out(order, db)


@router.delete("/{order_id}/items/{item_id}", response_model=OrderOut)
def delete_order_item(
    order_id: uuid.UUID,
    item_id: uuid.UUID,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> OrderOut:
    """Staff remove an item; the last item can't be removed (cancel the order instead)."""
    order = _get_store_order(db, current_store, order_id, lock=True)
    store_order_edit_service.remove_item(db, order, item_id)
    db.commit()
    db.refresh(order)
    return _order_out(order, db)


@router.get("/{order_id}/events", response_model=list[OrderEventOut])
def list_order_events(
    order_id: uuid.UUID,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> list[OrderEventOut]:
    """Change history of an order, oldest first."""
    order = _get_store_order(db, current_store, order_id)
    events = db.execute(
        select(OrderEvent).where(OrderEvent.order_id == order.id).order_by(OrderEvent.created_at)
    ).scalars().all()
    return [OrderEventOut.model_validate(e, from_attributes=True) for e in events]


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
