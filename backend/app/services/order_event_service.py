"""The change history shown on an order (order_events)."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.order_event import OrderEvent

ACTOR_STORE = "store"
ACTOR_CUSTOMER = "customer"
# Stripe-driven changes: payments, refunds and disputes reported by webhook.
ACTOR_STRIPE = "stripe"


def log_event(
    db: Session,
    order: Order,
    *,
    actor: str,
    kind: str,
    detail: str,
    total_before: Decimal | None = None,
) -> None:
    db.add(
        OrderEvent(
            order_id=order.id,
            actor=actor,
            kind=kind,
            detail=detail[:512],
            total_before=total_before if total_before is not None else order.total,
            total_after=order.total,
        )
    )
