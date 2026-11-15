"""Store-funded promotions: every discount amount is computed here, in code.

The voice assistant never works out a discount. It reads `discount`, `total`
and `next_promotion` from the order summary that the tools return.

Rules:
- A promotion applies automatically when the order qualifies: it is active,
  in its date range (store-local order day), covers the order's channel, and
  the pre-tax subtotal reaches its minimum.
- While the order is a draft, it gets the qualifying promotion that saves the
  customer the most. Store promotions never stack with each other.
- Once placed, the order keeps that promotion. Staff edits recompute the
  discount with it (zero while the subtotal is under its minimum), even if the
  store has since ended the promotion.
- The discount comes off the subtotal before tax and before commission.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.promotion import Promotion
from app.services import commission

ZERO = Decimal("0.00")
CENT = Decimal("0.01")
PERCENT, AMOUNT_OFF = "percent", "amount_off"
CHANNELS = ("all", "app", "phone")


def discount_for(promo: Promotion, subtotal: Decimal) -> Decimal:
    """What `promo` takes off this pre-tax subtotal (never more than the subtotal)."""
    if subtotal <= 0 or subtotal < promo.min_subtotal:
        return ZERO
    if promo.kind == PERCENT:
        off = (subtotal * promo.value / Decimal(100)).quantize(CENT, rounding=ROUND_HALF_UP)
    else:
        off = promo.value
    return min(off, subtotal)


def covers_channel(promo: Promotion, channel: str) -> bool:
    if promo.channels == "all":
        return True
    return (promo.channels == "phone") == commission.is_phone(channel)


def is_running(promo: Promotion, day: date) -> bool:
    return (
        promo.is_active
        and (promo.starts_on is None or promo.starts_on <= day)
        and (promo.ends_on is None or day <= promo.ends_on)
    )


def running_for(db: Session, *, store_id, channel: str | None, day: date) -> list[Promotion]:
    """The store's promotions an order on this channel (None: any) and day can get."""
    rows = db.execute(
        select(Promotion).where(Promotion.store_id == store_id, Promotion.is_active.is_(True)).order_by(Promotion.created_at)
    ).scalars()
    return [p for p in rows if is_running(p, day) and (channel is None or covers_channel(p, channel))]


def apply(db: Session, order: Order) -> None:
    """Set order.promotion_id and order.discount from order.subtotal."""
    if order.status == "draft":
        best, best_off = None, ZERO
        for promo in running_for(db, store_id=order.store_id, channel=order.channel, day=order.code_day):
            off = discount_for(promo, order.subtotal)
            if off > best_off:  # ties keep the older promotion
                best, best_off = promo, off
        order.promotion_id = best.id if best else None
        order.discount = best_off
        return
    promo = db.get(Promotion, order.promotion_id) if order.promotion_id else None
    order.discount = discount_for(promo, order.subtotal) if promo else ZERO


@dataclass(frozen=True)
class NextPromotion:
    name: str
    add_more: Decimal  # how much more subtotal reaches it
    discount: Decimal  # what it would take off at exactly that subtotal


def next_promotion(db: Session, order: Order) -> NextPromotion | None:
    """The nearest promotion the draft would get by adding a bit more, if that
    beats the current discount. For the assistant to mention; computed here."""
    if order.status != "draft" or order.subtotal <= 0:
        return None
    options = []
    for promo in running_for(db, store_id=order.store_id, channel=order.channel, day=order.code_day):
        if promo.min_subtotal <= order.subtotal:
            continue
        off = discount_for(promo, promo.min_subtotal)
        if off > order.discount:
            options.append(NextPromotion(name=promo.name, add_more=promo.min_subtotal - order.subtotal, discount=off))
    return min(options, key=lambda n: n.add_more, default=None)


def describe(promo: Promotion) -> str:
    """Plain-English terms, e.g. "10% off orders of $20.00 or more (phone orders only)"."""
    off = f"{promo.value.normalize():f}% off" if promo.kind == PERCENT else f"${promo.value:.2f} off"
    terms = f"{off} orders of ${promo.min_subtotal:.2f} or more" if promo.min_subtotal > 0 else f"{off} any order"
    if promo.channels != "all":
        terms += f" ({promo.channels} orders only)"
    return terms
