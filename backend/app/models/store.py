from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow_naive
from app.db.base import Base


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)

    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)

    allow_pickup: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_delivery: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Geocoded from the address fields above on save. Used together with
    # delivery_radius_km to gate whether a customer's delivery address falls
    # inside the store's delivery area (haversine distance check).
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    delivery_radius_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_order_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0.0000"))
    voice_tone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # List of {"raw": str, "generated": str} entries — one per store-defined rule.
    custom_prompts: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Stripe Connect (Express) connected-account id (acct_...). Set once the
    # store completes Stripe-hosted onboarding; payments for this store's orders
    # are routed here via destination charges.
    stripe_account_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Cached from Stripe (account.updated webhook): whether the store can accept
    # charges yet. Drives payment-ready badges; NOT a gate on orderability.
    stripe_charges_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    # Per-store commission override in basis points (e.g. 1000 = 10%). None
    # falls back to the platform default (settings.platform_fee_bps).
    platform_fee_bps: Mapped[int | None] = mapped_column(Integer, nullable=True)

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    # Platform approval gate (admin-controlled). A store is orderable only when
    # is_approved AND is_published AND is_active.
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow_naive)
