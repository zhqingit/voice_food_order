"""Platform promotions: discounts VoxEats funds out of its own commission.

Every amount is computed here, in code; the assistant only reads the
`online_offer` that the order summary carries.

Rules:
- Only for orders paid online in the app (a signed-in customer and a store
  that takes card payments). The discount is taken off the card charge, so the
  store's share is unchanged: what we give the customer comes out of our
  application fee.
- It stacks with the store's own promotion and is computed on the subtotal
  after that discount (pre-tax). Tax is unaffected.
- Never more than the commission we haven't collected on the order (we don't
  pay out of pocket), never more than the promotion's remaining monthly
  budget, and it leaves at least Stripe's $0.50 minimum to charge.
- One platform promotion per order: the first online payment fixes it. A
  later balance payment (staff raised the total) gets no further discount.
- Optional limits: first order only, uses per customer, monthly budget.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.order import Order
from app.models.payment import Payment
from app.models.promotion import Promotion
from app.models.store import Store
from app.services import order_payments, promotions

ZERO = Decimal("0.00")
STRIPE_MIN_CHARGE = Decimal("0.50")


@dataclass(frozen=True)
class Offer:
    promotion: Promotion
    discount: Decimal


def running(db: Session, *, channel: str, day: date) -> list[Promotion]:
    rows = db.execute(
        select(Promotion).where(Promotion.store_id.is_(None), Promotion.is_active.is_(True)).order_by(Promotion.created_at)
    ).scalars()
    return [p for p in rows if promotions.is_running(p, day) and promotions.covers_channel(p, channel)]


def _month_bounds(day: date) -> tuple[datetime, datetime]:
    start = date(day.year, day.month, 1)
    end = date(day.year + day.month // 12, day.month % 12 + 1, 1)
    return datetime.combine(start, datetime.min.time()), datetime.combine(end, datetime.min.time())


def spent_this_month(db: Session, promo: Promotion, day: date) -> Decimal:
    """Discount given through succeeded card charges this month (platform timezone)."""
    start, end = _month_bounds(day)
    local = func.timezone(settings.store_default_timezone, func.timezone("UTC", Payment.created_at))
    total = db.execute(
        select(func.sum(Payment.platform_discount))
        .join(Order, Order.id == Payment.order_id)
        .where(Order.platform_promotion_id == promo.id)
        .where(Payment.kind == "charge", Payment.status == "succeeded")
        .where(local >= start, local < end)
    ).scalar()
    return Decimal(total or 0)


def _uses_by_customer(db: Session, promo: Promotion, user_id: uuid.UUID, order_id: uuid.UUID) -> int:
    return db.execute(
        select(func.count())
        .select_from(Order)
        .where(Order.platform_promotion_id == promo.id, Order.user_id == user_id)
        .where(Order.platform_discount > 0, Order.id != order_id)
    ).scalar_one()


def _has_earlier_order(db: Session, user_id: uuid.UUID, order_id: uuid.UUID) -> bool:
    return db.execute(
        select(Order.id)
        .where(Order.user_id == user_id, Order.id != order_id)
        .where(Order.status.notin_(("draft", "cancelled")))
        .limit(1)
    ).first() is not None


def offer_for(db: Session, order: Order, *, amount_due: Decimal | None = None) -> Offer | None:
    """The platform discount this order gets if paid online now, or None.

    `amount_due` is what the card charge would be before the discount (the
    balance); the discount leaves at least Stripe's minimum to charge.
    """
    if order.user_id is None or order.platform_discount > 0 or order.status == "cancelled":
        return None
    store = db.get(Store, order.store_id)
    if store is None or not store.stripe_account_id or not store.stripe_charges_enabled:
        return None

    base = order.subtotal - order.discount
    uncollected = order.commission - order_payments.ledger(db, order).commission_collected
    room = min(uncollected, (amount_due if amount_due is not None else order.total) - STRIPE_MIN_CHARGE)
    if room <= 0:
        return None

    best: Offer | None = None
    for promo in running(db, channel=order.channel, day=order.code_day):
        if promo.first_order_only and _has_earlier_order(db, order.user_id, order.id):
            continue
        if promo.per_user_limit is not None and _uses_by_customer(db, promo, order.user_id, order.id) >= promo.per_user_limit:
            continue
        off = promotions.discount_for(promo, base)
        if promo.monthly_budget is not None:
            off = min(off, max(promo.monthly_budget - spent_this_month(db, promo, order.code_day), ZERO))
        off = min(off, room)
        if off > 0 and (best is None or off > best.discount):
            best = Offer(promotion=promo, discount=off)
    return best
