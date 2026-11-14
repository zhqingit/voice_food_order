from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import date, datetime

from pydantic import BaseModel, Field


class OrderItemOut(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    menu_item_id: uuid.UUID
    name: str | None = None
    quantity: int
    price_snapshot: Decimal
    note: str | None = None
    variant_name: str | None = None


class OrderOut(BaseModel):
    id: uuid.UUID
    short_code: str
    code_day: date
    store_id: uuid.UUID
    store_name: str | None = None
    # My Orders: unpaid, still open, and the store takes online payment.
    can_pay_online: bool = False
    # My Orders: the store's phone, so the customer can call about the order.
    store_phone: str | None = None
    # My Orders: staff changed the items after the order was placed.
    modified_by_store: bool = False
    user_id: uuid.UUID | None
    status: str
    payment_status: str = "unpaid"
    channel: str
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    customer_name: str | None = None
    customer_phone: str | None = None
    user_email: str | None = None
    notes: str | None
    fulfillment_type: str | None = None
    delivery_address: str | None = None
    created_at: datetime


class OrderItemCreate(BaseModel):
    menu_item_id: uuid.UUID
    quantity: int = Field(ge=1)


class OrderCreate(BaseModel):
    store_id: uuid.UUID
    user_id: uuid.UUID | None = None
    channel: str = Field(min_length=2, max_length=32)
    notes: str | None = Field(default=None, max_length=1024)
    items: list[OrderItemCreate] = Field(default_factory=list)


class OrderStatusUpdate(BaseModel):
    status: str = Field(min_length=2, max_length=32)


class StoreOrderItemAdd(BaseModel):
    menu_item_id: uuid.UUID
    # Required when the menu item has options (sizes, can/bottle, ...).
    variant_id: uuid.UUID | None = None
    quantity: int = Field(default=1, ge=1, le=99)
    note: str | None = Field(default=None, max_length=512)


class StoreOrderItemUpdate(BaseModel):
    quantity: int | None = Field(default=None, ge=1, le=99)
    # Send "" or null to remove the note; leave it out to keep it.
    note: str | None = Field(default=None, max_length=512)


class OrderEventOut(BaseModel):
    id: uuid.UUID
    actor: str
    kind: str
    detail: str
    total_before: Decimal | None = None
    total_after: Decimal | None = None
    created_at: datetime
