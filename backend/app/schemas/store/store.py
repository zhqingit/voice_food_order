from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class StoreOut(BaseModel):
    id: uuid.UUID
    name: str
    phone: str | None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    timezone: str | None = None
    allow_pickup: bool | None = None
    allow_delivery: bool | None = None
    min_order_amount: Decimal | None = None
    email: EmailStr
    created_at: datetime


class StoreUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, max_length=64)
    address_line1: str | None = Field(default=None, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=255)
    state: str | None = Field(default=None, max_length=255)
    postal_code: str | None = Field(default=None, max_length=64)
    country: str | None = Field(default=None, max_length=64)
    timezone: str | None = Field(default=None, max_length=64)
    allow_pickup: bool | None = None
    allow_delivery: bool | None = None
    min_order_amount: Decimal | None = None
