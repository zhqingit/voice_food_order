from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.core.phone import normalize_phone


class AdminStoreOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    phone: str | None
    # Orderability gates (customer sees the store only when all three are true).
    is_published: bool
    is_approved: bool
    is_active: bool
    # Payments
    stripe_account_id: str | None
    stripe_charges_enabled: bool
    # Commission in basis points on the pre-tax subtotal, by order channel:
    # the store's override (None = platform default) and the rate in effect.
    commission_app_bps: int | None
    commission_phone_bps: int | None
    effective_app_bps: int
    effective_phone_bps: int
    # Flat monthly fee on the store's invoice (0 = none).
    monthly_fee: Decimal
    # Phone ordering
    phone_ai_number: str | None
    phone_ai_enabled: bool
    created_at: datetime


class AdminStoreDetailOut(AdminStoreOut):
    # Live Stripe status, best-effort (None when not connected or fetch failed).
    stripe_details_submitted: bool | None = None
    stripe_payouts_enabled: bool | None = None


class AdminStoreUpdate(BaseModel):
    is_approved: bool | None = None
    is_active: bool | None = None
    # Send null to clear an override (fall back to the platform default);
    # omit the field to leave it unchanged.
    commission_app_bps: int | None = Field(default=None, ge=0, le=10000)
    commission_phone_bps: int | None = Field(default=None, ge=0, le=10000)
    monthly_fee: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    # The Twilio number routed to this store. Send null to unassign it.
    phone_ai_number: str | None = Field(default=None, max_length=32)

    @field_validator("phone_ai_number")
    @classmethod
    def _normalize_ai_number(cls, value: str | None) -> str | None:
        return normalize_phone(value) if value and value.strip() else None
