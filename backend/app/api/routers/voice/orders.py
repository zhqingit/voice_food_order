from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.user import get_current_user_mobile
from app.api.host_policy import require_host_policy
from app.core.config import settings
from app.core.errors import AppError
from app.db.session import get_db
from app.models.menu_item import MenuItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.store import Store
from app.models.user import User
from app.schemas.common import Audience, PrincipalType
from app.schemas.order.order import OrderCreate, OrderItemCreate, OrderItemOut, OrderOut
from app.schemas.order.payment import PaymentIntentResponse
from app.services import order_service, payment_service

from pydantic import BaseModel, Field


class OrderPatch(BaseModel):
    delivery_address: str | None = Field(default=None, max_length=512)
    fulfillment_type: str | None = Field(default=None, pattern="^(pickup|delivery)$")
    customer_name: str | None = Field(default=None, max_length=128)

router = APIRouter(
    prefix="/voice/orders",
    tags=["voice-orders"],
    dependencies=[Depends(require_host_policy(principal=PrincipalType.user, audience=Audience.mobile))],
)


def _order_out(order: Order) -> OrderOut:
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


@router.post("/draft", response_model=OrderOut)
def create_draft(
    payload: OrderCreate,
    current_user: User = Depends(get_current_user_mobile),
    db: Session = Depends(get_db),
) -> OrderOut:
    """Create a new draft order for the current user. 
    The order will be created with status 'draft' and can be updated later to add items, submit, etc."""
    payload = payload.model_copy(update={"user_id": current_user.id, "channel": "voice"})
    order = order_service.create_draft_order(db, payload=payload)
    db.commit()
    db.refresh(order)
    return _order_out(order)


@router.get("/{order_id}", response_model=OrderOut)
def get_order_summary(
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


@router.patch("/{order_id}", response_model=OrderOut)
def patch_order(
    order_id: uuid.UUID,
    payload: OrderPatch,
    current_user: User = Depends(get_current_user_mobile),
    db: Session = Depends(get_db),
) -> OrderOut:
    """Update editable fields on a draft voice order owned by the current user."""
    order = db.execute(
        select(Order).where(Order.user_id == current_user.id).where(Order.id == order_id)
    ).scalar_one_or_none()
    if order is None:
        raise AppError(status_code=404, code="order_not_found", detail="Order not found")
    if order.status != "draft":
        raise AppError(status_code=409, code="order_not_editable", detail="Order is not editable")

    updates = payload.model_dump(exclude_unset=True)
    # If the customer edits the delivery address in the app, the prior verbal
    # confirmation no longer applies — the bot must re-confirm before checkout.
    if "delivery_address" in updates:
        old = (order.delivery_address or "").strip().lower()
        new = (updates["delivery_address"] or "").strip().lower()
        if old != new:
            order.delivery_confirmed_at = None
    if "fulfillment_type" in updates and updates["fulfillment_type"] != order.fulfillment_type:
        order.delivery_confirmed_at = None
    for key, value in updates.items():
        setattr(order, key, value)
    db.commit()
    db.refresh(order)
    return _order_out(order)


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


@router.post("/{order_id}/items", response_model=OrderItemOut)
def add_order_item(
    order_id: uuid.UUID,
    payload: OrderItemCreate,
    current_user: User = Depends(get_current_user_mobile),
    db: Session = Depends(get_db),
) -> OrderItemOut:
    order = db.execute(
        select(Order).where(Order.user_id == current_user.id).where(Order.id == order_id)
    ).scalar_one_or_none()
    if order is None:
        raise AppError(status_code=404, code="order_not_found", detail="Order not found")
    if order.status != "draft":
        raise AppError(status_code=409, code="order_not_editable", detail="Order is not editable")

    menu_item = order_service.get_menu_item_for_store(db, store_id=order.store_id, item_id=payload.menu_item_id)
    if menu_item is None:
        raise AppError(status_code=404, code="menu_item_not_found", detail="Menu item not found")

    item = order_service.create_order_item(db, order=order, menu_item=menu_item, quantity=payload.quantity)
    order_service.recalc_totals(db, order=order)
    db.commit()
    db.refresh(item)
    return _order_item_out(item)


@router.delete("/{order_id}/items/{item_id}")
def remove_order_item(
    order_id: uuid.UUID,
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user_mobile),
    db: Session = Depends(get_db),
) -> dict:
    """Remove an item from a draft order. Order must belong to the current user."""
    order = db.execute(
        select(Order).where(Order.user_id == current_user.id).where(Order.id == order_id)
    ).scalar_one_or_none()
    if order is None:
        raise AppError(status_code=404, code="order_not_found", detail="Order not found")
    if order.status != "draft":
        raise AppError(status_code=409, code="order_not_editable", detail="Order is not editable")

    order_service.remove_order_item(db, order=order, item_id=item_id)
    order_service.recalc_totals(db, order=order)
    db.commit()
    return {"status": "ok"}


@router.post("/{order_id}/finalize", response_model=OrderOut)
def finalize_order(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user_mobile),
    db: Session = Depends(get_db),
) -> OrderOut:
    """Finalize a draft order. Order must belong to the current user."""
    order = db.execute(
        select(Order).where(Order.user_id == current_user.id).where(Order.id == order_id)
    ).scalar_one_or_none()
    if order is None:
        raise AppError(status_code=404, code="order_not_found", detail="Order not found")
    if order.status != "draft":
        raise AppError(status_code=409, code="order_not_editable", detail="Order is not editable")

    order.status = "submitted"
    order_service.recalc_totals(db, order=order)
    db.commit()
    db.refresh(order)
    return _order_out(order)


@router.post("/{order_id}/payment-intent", response_model=PaymentIntentResponse)
def create_payment_intent(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user_mobile),
    db: Session = Depends(get_db),
) -> PaymentIntentResponse:
    """Start an online payment for an order owned by the current user.

    If the store isn't payment-ready, returns payment_available=False so the
    client falls back to collecting at the store instead of charging online.
    """
    order = db.execute(
        select(Order).where(Order.user_id == current_user.id).where(Order.id == order_id)
    ).scalar_one_or_none()
    if order is None:
        raise AppError(status_code=404, code="order_not_found", detail="Order not found")
    if order.payment_status == "paid":
        raise AppError(status_code=409, code="already_paid", detail="Order is already paid")

    store = db.get(Store, order.store_id)
    if store is None:
        raise AppError(status_code=404, code="store_not_found", detail="Store not found")

    amount = payment_service.to_cents(order.total)

    # Store not payment-ready → tell the client to collect at the store.
    if not store.stripe_account_id or not store.stripe_charges_enabled:
        return PaymentIntentResponse(
            payment_available=False,
            amount=amount,
            reason="store_not_payment_ready",
        )

    result = payment_service.create_payment_intent(order, store)
    order.payment_ref = result.payment_intent_id
    db.add(order)
    db.commit()

    return PaymentIntentResponse(
        payment_available=True,
        client_secret=result.client_secret,
        publishable_key=settings.stripe_publishable_key,
        amount=amount,
    )
