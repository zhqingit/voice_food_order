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
- Never more than the order's commission (we don't pay out of pocket), never
  more than the promotion's remaining monthly budget, and it leaves at least
  Stripe's $0.50 minimum to charge.
- Only the first online payment of an order can get one. Once a card payment
  has succeeded, later balance payments (staff raised the total) get none.
- Optional limits: first order only, uses per customer, monthly budget. A
  payment in progress counts toward them for an hour (an abandoned payment
  sheet stops holding the discount after that).

offer_for() is the check at payment time. A voice session loads the
eligibility once (load_eligible) and previews the offer in memory each turn
(preview_offer); the payment still re-checks everything.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.time import utcnow_naive
from app.models.order import Order
from app.models.payment import Payment
from app.models.promotion import Promotion
from app.models.store import Store
from app.schemas.order.order import OrderOut
from app.services import months, order_payments, promotions
from app.services.promotions import PromoTerms

ZERO = Decimal("0.00")
# How long a started (unfinished) card payment holds its discount against the limits.
PENDING_HOLD = timedelta(hours=1)


@dataclass(frozen=True)
class Eligible:
    promotion: PromoTerms
    budget_left: Decimal | None  # None = no monthly budget


@dataclass(frozen=True)
class Offer:
    promotion: PromoTerms
    discount: Decimal


def running(db: Session, *, channel: str, day: date) -> list[Promotion]:
    rows = db.execute(
        select(Promotion).where(Promotion.store_id.is_(None), Promotion.is_active.is_(True)).order_by(Promotion.created_at)
    ).scalars()
    return [p for p in rows if promotions.is_running(p, day) and promotions.covers_channel(p, channel)]


def _counted(now: datetime):
    """Card charges that count toward the limits: succeeded, or started within the hold."""
    return (Payment.kind == "charge") & (
        (Payment.status == "succeeded") | ((Payment.status == "pending") & (Payment.created_at >= now - PENDING_HOLD))
    )


def spent_this_month(db: Session, promo_id: uuid.UUID, today: date, exclude_order: uuid.UUID | None = None) -> Decimal:
    """Discount this promotion gave (or is giving, see PENDING_HOLD) this month, platform timezone."""
    start = today.replace(day=1)
    query = (
        select(func.sum(Payment.platform_discount))
        .where(Payment.platform_promotion_id == promo_id, _counted(utcnow_naive()))
        .where(months.in_month(Payment.created_at, start, months.shift_month(start, 1)))
    )
    if exclude_order is not None:
        query = query.where(Payment.order_id != exclude_order)
    return Decimal(db.execute(query).scalar() or 0)


def _uses_by_customer(db: Session, promo_id: uuid.UUID, user_id: uuid.UUID, exclude_order: uuid.UUID | None) -> int:
    query = (
        select(func.count(func.distinct(Payment.order_id)))
        .join(Order, Order.id == Payment.order_id)
        .where(Payment.platform_promotion_id == promo_id, Order.user_id == user_id, _counted(utcnow_naive()))
    )
    if exclude_order is not None:
        query = query.where(Order.id != exclude_order)
    return db.execute(query).scalar_one()


def _has_earlier_order(db: Session, user_id: uuid.UUID, order: Order | None) -> bool:
    """Has the customer placed an order before this one? (None: before now, for a new draft.)"""
    query = select(Order.id).where(Order.user_id == user_id).where(Order.status.notin_(("draft", "cancelled")))
    if order is not None:
        query = query.where(Order.id != order.id, Order.created_at < order.created_at)
    return db.execute(query.limit(1)).first() is not None


def _store_takes_cards(db: Session, store_id: uuid.UUID) -> bool:
    store = db.get(Store, store_id)
    return store is not None and bool(store.stripe_account_id) and store.stripe_charges_enabled


def load_eligible(
    db: Session, *, user_id: uuid.UUID | None, store_id: uuid.UUID, channel: str, day: date, order: Order | None = None
) -> list[Eligible]:
    """The platform promotions this customer qualifies for right now, with what's left of each budget."""
    if user_id is None or not _store_takes_cards(db, store_id):
        return []
    today = months.platform_today()
    out = []
    for p in running(db, channel=channel, day=day):
        if p.first_order_only and _has_earlier_order(db, user_id, order):
            continue
        if p.per_user_limit is not None and _uses_by_customer(db, p.id, user_id, order.id if order else None) >= p.per_user_limit:
            continue
        spent = ZERO if p.monthly_budget is None else spent_this_month(db, p.id, today, order.id if order else None)
        left = None if p.monthly_budget is None else max(p.monthly_budget - spent, ZERO)
        if left is not None and left <= 0:
            continue
        out.append(Eligible(promotion=PromoTerms.of(p), budget_left=left))
    return out


def best_offer(eligible: list[Eligible], *, base: Decimal, room: Decimal) -> Offer | None:
    """The largest discount among `eligible` on this pre-tax base, capped by `room`. Pure."""
    best: Offer | None = None
    for e in eligible:
        off = promotions.discount_for(e.promotion, base)
        if e.budget_left is not None:
            off = min(off, e.budget_left)
        off = min(off, room)
        if off > 0 and (best is None or off > best.discount):
            best = Offer(promotion=e.promotion, discount=off)
    return best


def _room(order: Order, amount_due: Decimal) -> Decimal:
    # No card payment has succeeded yet (see offer_for), so nothing of the commission is collected.
    return min(order.commission, amount_due - order_payments.STRIPE_MIN_CHARGE)


def offer_for(db: Session, order: Order, *, amount_due: Decimal | None = None) -> Offer | None:
    """The platform discount this order gets if paid online now (the check at payment time)."""
    if order.user_id is None or order.status == "cancelled" or order.platform_discount > 0:
        return None
    if order_payments.ledger(db, order).paid > 0:
        return None  # only the first online payment of an order
    eligible = load_eligible(
        db, user_id=order.user_id, store_id=order.store_id, channel=order.channel, day=order.code_day, order=order
    )
    due = amount_due if amount_due is not None else order.total
    return best_offer(eligible, base=order.subtotal - order.discount, room=_room(order, due))


def preview_offer(eligible: list[Eligible], order: Order) -> Offer | None:
    """For a voice session's draft, from eligibility loaded once at the start. No queries."""
    if not eligible or order.subtotal <= 0:
        return None
    return best_offer(eligible, base=order.subtotal - order.discount, room=_room(order, order.total))


def with_online_offer(db: Session, out: OrderOut, order: Order, *, balance_due: Decimal) -> OrderOut:
    """Fill OrderOut.online_offer for the customer app (unpaid, payable orders only)."""
    if balance_due < order_payments.STRIPE_MIN_CHARGE:
        return out
    offer = offer_for(db, order, amount_due=balance_due)
    if offer is not None:
        out.online_offer, out.online_offer_name = offer.discount, offer.promotion.name
    return out
