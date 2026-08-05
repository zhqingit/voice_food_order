from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


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
    platform_fee_bps: int | None  # store override; None = platform default
    effective_fee_bps: int  # resolved commission actually applied
    created_at: datetime


class AdminStoreDetailOut(AdminStoreOut):
    # Live Stripe status, best-effort (None when not connected or fetch failed).
    stripe_details_submitted: bool | None = None
    stripe_payouts_enabled: bool | None = None


class AdminStoreUpdate(BaseModel):
    is_approved: bool | None = None
    is_active: bool | None = None
    # Send null to clear the override (fall back to the platform default);
    # omit the field to leave it unchanged.
    platform_fee_bps: int | None = Field(default=None, ge=0, le=10000)
