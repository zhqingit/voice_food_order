from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel, Field


class OrderItemOut(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    menu_item_id: uuid.UUID
    quantity: int
    price_snapshot: Decimal


class OrderOut(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    user_id: uuid.UUID | None
    status: str
    channel: str
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    notes: str | None
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
