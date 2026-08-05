from __future__ import annotations

from pydantic import BaseModel


class PaymentIntentResponse(BaseModel):
    # False when the store isn't payment-ready — the client should collect at
    # the store instead of charging online.
    payment_available: bool
    client_secret: str | None = None
    publishable_key: str | None = None
    amount: int  # order total in cents
    currency: str = "usd"
    reason: str | None = None  # why payment is unavailable, when applicable
