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
    # None until the store enters one (0 is a valid rate); required to publish.
    tax_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
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
    # Stripe Customer (cus_...) on the platform account that the store's
    # monthly invoices are billed to. Created on the first invoice sent.
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Per-store commission overrides in basis points (e.g. 1500 = 15%), by order
    # channel. None falls back to the platform default (settings.commission_*_bps).
    commission_app_bps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    commission_phone_bps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Flat monthly fee added to the store's monthly invoice. 0 = none.
    monthly_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00"), server_default="0"
    )

    # Phone ordering. phone_ai_number (E.164) is the Twilio number whose calls
    # reach this store's voice bot; admin-assigned so a store can't claim
    # another store's line. phone_staff_number is where callers asking for a
    # person are transferred; it must not forward back to phone_ai_number.
    phone_ai_number: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    phone_ai_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    phone_staff_number: Mapped[str | None] = mapped_column(String(20), nullable=True)

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    # Platform approval gate (admin-controlled). A store is orderable only when
    # is_approved AND is_published AND is_active.
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow_naive)
