"""Staff edits to placed orders from the store portal.

Customers can't change an order once it is placed; they contact the store and
staff edit it here. Every change recalculates the totals and is written to
order_events.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.menu_item import MenuItem
from app.models.menu_item_variant import MenuItemVariant
from app.models.order import Order
from app.models.order_item import OrderItem
from app.services import order_payments, order_service
from app.services.order_event_service import ACTOR_STORE, log_event


def _require_editable(order: Order) -> None:
    if order.status not in order_service.OPEN_STATUSES:
        raise AppError(status_code=409, code="order_not_editable", detail="This order can no longer be edited")


def _item_label(db: Session, item: OrderItem) -> str:
    menu_item = db.get(MenuItem, item.menu_item_id)
    name = menu_item.name if menu_item else "Unknown item"
    return f"{name} ({item.variant_name})" if item.variant_name else name


def _get_item(db: Session, order: Order, item_id: uuid.UUID) -> OrderItem:
    item = db.execute(
        select(OrderItem).where(OrderItem.order_id == order.id).where(OrderItem.id == item_id)
    ).scalar_one_or_none()
    if item is None:
        raise AppError(status_code=404, code="order_item_not_found", detail="Order item not found")
    return item


def _recalc_and_log(db: Session, order: Order, *, kind: str, detail: str) -> None:
    total_before = order.total
    db.flush()
    order_service.recalc_totals(db, order=order)
    # A paid order whose total went up now has a balance due (or, if it went
    # down, an overpayment staff can refund).
    order_payments.sync_payment_status(db, order)
    log_event(db, order, actor=ACTOR_STORE, kind=kind, detail=detail, total_before=total_before)


def add_item(
    db: Session,
    order: Order,
    *,
    menu_item_id: uuid.UUID,
    variant_id: uuid.UUID | None,
    quantity: int,
    note: str | None,
) -> None:
    _require_editable(order)
    menu_item = order_service.get_menu_item_for_store(db, store_id=order.store_id, item_id=menu_item_id)
    if menu_item is None:
        raise AppError(status_code=404, code="menu_item_not_found", detail="Menu item not found")

    variants = list(menu_item.variants or [])
    variant: MenuItemVariant | None = None
    if variants:
        variant = next((v for v in variants if v.id == variant_id), None)
        if variant is None:
            raise AppError(status_code=422, code="variant_required", detail="Choose one of this item's options")
    elif variant_id is not None:
        raise AppError(status_code=422, code="variant_invalid", detail="This item has no options")

    note = (note or "").strip() or None
    item = order_service.create_order_item(
        db,
        order=order,
        menu_item=menu_item,
        quantity=quantity,
        price_override=variant.price if variant else menu_item.price,
        note=note,
    )
    item.variant_name = variant.name if variant else None
    _recalc_and_log(db, order, kind="item_added", detail=f"{quantity} × {_item_label(db, item)}")


def update_item(
    db: Session,
    order: Order,
    item_id: uuid.UUID,
    *,
    quantity: int | None,
    note: str | None,
    note_set: bool,
) -> None:
    _require_editable(order)
    item = _get_item(db, order, item_id)
    changes = []
    if quantity is not None and quantity != item.quantity:
        changes.append(f"×{item.quantity} → ×{quantity}")
        item.quantity = quantity
    if note_set:
        new_note = (note or "").strip() or None
        if new_note != item.note:
            changes.append(f'note: "{new_note}"' if new_note else "note removed")
            item.note = new_note
    if changes:
        _recalc_and_log(db, order, kind="item_updated", detail=f"{_item_label(db, item)}: {', '.join(changes)}")


def remove_item(db: Session, order: Order, item_id: uuid.UUID) -> None:
    _require_editable(order)
    item = _get_item(db, order, item_id)
    remaining = db.execute(
        select(OrderItem.id).where(OrderItem.order_id == order.id).where(OrderItem.id != item.id).limit(1)
    ).first()
    if remaining is None:
        raise AppError(
            status_code=409, code="last_item", detail="An order needs at least one item; cancel the order instead"
        )
    label = f"{item.quantity} × {_item_label(db, item)}"
    db.delete(item)
    _recalc_and_log(db, order, kind="item_removed", detail=label)


def set_status(db: Session, order: Order, status: str, *, actor: str = ACTOR_STORE) -> None:
    if status == order.status:
        return
    log_event(db, order, actor=actor, kind="status_changed", detail=f"{order.status} → {status}")
    order.status = status
    if status == order_payments.CANCELLED:
        order_payments.on_cancelled(db, order)
    # A cancelled order owes nothing, so what was paid becomes refundable.
    order_payments.sync_payment_status(db, order)
