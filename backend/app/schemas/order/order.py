from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import date, datetime

from typing import Literal

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
    # My Orders: when staff last changed the items or cancelled the order, so the
    # app can point it out until the customer has looked.
    store_changed_at: datetime | None = None
    user_id: uuid.UUID | None
    status: str
    # unpaid | partially_paid | paid | refunded
    payment_status: str = "unpaid"
    # Net amount paid so far (charges minus refunds), and what is still owed.
    amount_paid: Decimal = Decimal("0.00")
    balance_due: Decimal = Decimal("0.00")
    channel: str
    subtotal: Decimal  # before discount
    # Store promotion taken off the subtotal (before tax).
    discount: Decimal = Decimal("0.00")
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


class PaymentOut(BaseModel):
    id: uuid.UUID
    kind: str  # charge | refund
    method: str  # card | in_store | dispute
    amount: Decimal
    status: str  # pending | succeeded | failed | canceled
    failure_reason: str | None = None
    created_at: datetime


class OrderPaymentsOut(BaseModel):
    paid: Decimal
    refunded: Decimal
    net: Decimal
    balance_due: Decimal
    # Paid more than is owed (staff lowered the total, or the order was cancelled).
    overpaid: Decimal
    # How much can still go back to the customer's card through Stripe.
    card_refundable: Decimal
    payments: list[PaymentOut]


class RefundCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    method: Literal["card", "in_store"] = "card"


class InStorePaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class CustomerNoticeOut(BaseModel):
    message: str
    phone: str | None = None
    # Changes the customer hasn't been told about yet.
    pending: bool
    last_notified_at: datetime | None = None
    # Texting needs the A2P 10DLC registration; until then staff call.
    sms_available: bool = False


class CustomerNotifiedCreate(BaseModel):
    method: Literal["call", "sms"] = "call"
