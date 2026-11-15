from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

PromotionKind = Literal["percent", "amount_off"]
PromotionChannels = Literal["all", "app", "phone"]


class PromotionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: PromotionKind
    # Percent (10 = 10% off) or dollars off.
    value: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    min_subtotal: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=10, decimal_places=2)
    channels: PromotionChannels = "all"
    starts_on: date | None = None
    ends_on: date | None = None

    @model_validator(mode="after")
    def _check(self) -> "PromotionCreate":
        if self.kind == "percent" and self.value > 100:
            raise ValueError("A percent discount can't be more than 100%.")
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("The end date is before the start date.")
        return self


class PromotionUpdate(BaseModel):
    """Only the name, dates and on/off switch change; the terms are fixed."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    is_active: bool | None = None
    starts_on: date | None = None
    ends_on: date | None = None


class PromotionOut(BaseModel):
    id: uuid.UUID
    name: str
    kind: PromotionKind
    value: Decimal
    min_subtotal: Decimal
    channels: PromotionChannels
    starts_on: date | None
    ends_on: date | None
    is_active: bool
    # Orders placed with it (it can only be deleted while this is 0).
    orders_count: int
    created_at: datetime


class PromotionPublic(BaseModel):
    """A store's current promotion, as the customer app shows it."""

    id: uuid.UUID
    name: str
    kind: PromotionKind
    value: Decimal
    min_subtotal: Decimal
    channels: PromotionChannels


class PlatformPromotionCreate(PromotionCreate):
    """A VoxEats-funded promotion (admin). Applies only to orders paid online."""

    first_order_only: bool = False
    per_user_limit: int | None = Field(default=None, ge=1)
    monthly_budget: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)


class PlatformPromotionUpdate(PromotionUpdate):
    """The limits can change (they never alter past orders); the terms can't."""

    first_order_only: bool | None = None
    per_user_limit: int | None = Field(default=None, ge=1)
    monthly_budget: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)


class PlatformPromotionOut(PromotionOut):
    first_order_only: bool
    per_user_limit: int | None
    monthly_budget: Decimal | None
    # Discount given this month (platform timezone).
    spent_this_month: Decimal
