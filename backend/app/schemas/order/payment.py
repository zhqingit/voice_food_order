from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class PaymentIntentResponse(BaseModel):
    # False when the store isn't payment-ready — the client should collect at
    # the store instead of charging online.
    payment_available: bool
    client_secret: str | None = None
    publishable_key: str | None = None
    amount: int  # what the card is charged, in cents (after any platform discount)
    # Platform promotion taken off this online payment (computed by the server).
    platform_discount: Decimal = Decimal("0.00")
    promotion: str | None = None
    currency: str = "usd"
    reason: str | None = None  # why payment is unavailable, when applicable
