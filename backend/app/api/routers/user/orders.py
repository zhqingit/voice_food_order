from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.user import get_current_user_mobile
from app.api.host_policy import require_host_policy
from app.core.errors import AppError
from app.db.session import get_db
from app.models.menu_item import MenuItem
from app.models.order import Order
from app.models.order_event import OrderEvent
from app.models.order_item import OrderItem
from app.models.store import Store
from app.models.user import User
from app.schemas.common import Audience, PrincipalType
from app.schemas.order.order import OrderCreate, OrderItemOut, OrderOut
from app.services import order_payments, order_service, store_order_edit_service
from app.services.order_event_service import ACTOR_CUSTOMER, ACTOR_STORE

# Customers can cancel only before the store accepts the order; after that they call the store.
CUSTOMER_CANCELLABLE_STATUSES = frozenset({"submitted"})

router = APIRouter(
    prefix="/user/orders",
    tags=["user-orders"],
    dependencies=[Depends(require_host_policy(principal=PrincipalType.user, audience=Audience.mobile))],
)


def _order_out(
    order: Order,
    store: Store | None = None,
    *,
    modified_by_store: bool = False,
    store_changed_at: datetime | None = None,
    net_paid: Decimal = order_payments.ZERO,
) -> OrderOut:
    can_pay_online = (
        store is not None
        and order.payment_status != "paid"
        and order.status in order_service.PAYABLE_STATUSES
        and bool(store.stripe_account_id)
        and store.stripe_charges_enabled
    )
    return OrderOut(
        id=order.id,
        short_code=order.short_code,
        code_day=order.code_day,
        store_id=order.store_id,
        store_name=store.name if store is not None else None,
        can_pay_online=can_pay_online,
        store_phone=store.phone if store is not None else None,
        modified_by_store=modified_by_store,
        store_changed_at=store_changed_at,
        user_id=order.user_id,
        status=order.status,
        payment_status=order.payment_status,
        amount_paid=net_paid,
        balance_due=max(order_payments.owed(order) - net_paid, order_payments.ZERO),
        channel=order.channel,
        subtotal=order.subtotal,
        tax=order.tax,
        total=order.total,
        customer_name=order.customer_name,
        notes=order.notes,
        fulfillment_type=order.fulfillment_type,
        delivery_address=order.delivery_address,
        created_at=order.created_at,
    )


def _order_item_out(item: OrderItem, name: str | None = None) -> OrderItemOut:
    return OrderItemOut(
        id=item.id,
        order_id=item.order_id,
        menu_item_id=item.menu_item_id,
        name=name,
        quantity=item.quantity,
        price_snapshot=item.price_snapshot,
        note=item.note,
        variant_name=item.variant_name,
    )


@router.get("", response_model=list[OrderOut])
def list_orders(
    current_user: User = Depends(get_current_user_mobile),
    db: Session = Depends(get_db),
) -> list[OrderOut]:
    """List the current user's placed orders (drafts excluded), newest first."""
    rows = db.execute(
        select(Order, Store)
        .join(Store, Store.id == Order.store_id)
        .where(Order.user_id == current_user.id)
        .where(Order.status != "draft")
        .order_by(Order.created_at.desc())
    ).all()
    # Staff changes the customer should hear about: item edits, and the store cancelling.
    store_events = db.execute(
        select(OrderEvent.order_id, OrderEvent.kind, OrderEvent.created_at)
        .where(OrderEvent.order_id.in_([order.id for order, _ in rows]))
        .where(OrderEvent.actor == ACTOR_STORE)
        .where(
            OrderEvent.kind.like("item_%")
            | ((OrderEvent.kind == "status_changed") & OrderEvent.detail.like(f"%→ {order_payments.CANCELLED}"))
        )
    ).all()
    modified = {order_id for order_id, kind, _ in store_events if kind.startswith("item_")}
    store_changed_at: dict[uuid.UUID, datetime] = {}
    for order_id, _, created_at in store_events:
        store_changed_at[order_id] = max(created_at, store_changed_at.get(order_id, created_at))
    net_paid = order_payments.net_paid_by_order(db, [order.id for order, _ in rows])
    return [
        _order_out(
            order,
            store,
            modified_by_store=order.id in modified,
            store_changed_at=store_changed_at.get(order.id),
            net_paid=net_paid.get(order.id, order_payments.ZERO),
        )
        for order, store in rows
    ]


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user_mobile),
    db: Session = Depends(get_db),
) -> OrderOut:
    """Cancel an order the store hasn't accepted yet; card payments are refunded."""
    order = db.execute(
        select(Order).where(Order.user_id == current_user.id).where(Order.id == order_id).with_for_update()
    ).scalar_one_or_none()
    if order is None:
        raise AppError(status_code=404, code="order_not_found", detail="Order not found")
    if order.status not in CUSTOMER_CANCELLABLE_STATUSES:
        raise AppError(
            status_code=409,
            code="order_not_cancellable",
            detail="The restaurant has already accepted this order; please call them to cancel",
        )
    store_order_edit_service.set_status(db, order, order_payments.CANCELLED, actor=ACTOR_CUSTOMER)
    led = order_payments.ledger(db, order)
    refundable = min(led.overpaid, led.card_refundable)
    if refundable > 0:
        order_payments.refund(db, order, amount=refundable, method="card", actor=ACTOR_CUSTOMER)
    db.commit()
    db.refresh(order)
    store = db.get(Store, order.store_id)
    return _order_out(order, store, net_paid=order_payments.ledger(db, order).net)


@router.post("", response_model=OrderOut)
def create_order(
    payload: OrderCreate,
    current_user: User = Depends(get_current_user_mobile),
    db: Session = Depends(get_db),
) -> OrderOut:
    """Create a new draft order for the current user. 
    The order will be created with status 'draft' and can be updated later to add items, submit, etc."""
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
    """Get details of a specific order by ID. Order must belong to the current user."""
    order = db.execute(
        select(Order).where(Order.user_id == current_user.id).where(Order.id == order_id)
    ).scalar_one_or_none()
    if order is None:
        raise AppError(status_code=404, code="order_not_found", detail="Order not found")
    return _order_out(order)

# Note: we could combine this with the get_order endpoint and return items as a nested list, 
# but keeping it separate allows clients to fetch order details without necessarily fetching all items, 
# which could be beneficial for performance in some cases.
@router.get("/{order_id}/items", response_model=list[OrderItemOut])
def list_order_items(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user_mobile),
    db: Session = Depends(get_db),
) -> list[OrderItemOut]:
    """List items for a given order. Order must belong to the current user."""
    order = db.execute(
        select(Order).where(Order.user_id == current_user.id).where(Order.id == order_id)
    ).scalar_one_or_none()
    if order is None:
        raise AppError(status_code=404, code="order_not_found", detail="Order not found")

    rows = db.execute(
        select(OrderItem, MenuItem.name)
        .outerjoin(MenuItem, MenuItem.id == OrderItem.menu_item_id)
        .where(OrderItem.order_id == order.id)
    ).all()
    return [_order_item_out(item, name=name) for item, name in rows]
