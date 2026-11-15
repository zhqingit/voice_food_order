"""Money on a placed order: what was charged and refunded, what is still owed,
and how staff and customers move it.

Every charge and refund is a row in `payments`; the order's payment_status is
derived from them:
  unpaid          nothing paid
  partially_paid  something paid, but less than the total (staff raised it)
  paid            paid in full (or more: staff lowered the total, or cancelled)
  refunded        everything paid was refunded

Stripe calls go through payment_service.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.time import utcnow_naive
from app.models.order import Order
from app.models.order_event import OrderEvent
from app.models.payment import Payment
from app.models.store import Store
from app.services import payment_service
from app.services.order_event_service import ACTOR_STORE, ACTOR_STRIPE, log_event

CANCELLED = "cancelled"
ZERO = Decimal("0.00")
# A pending refund already counts, so the same money is never refunded twice.
REFUND_COUNTED = ("pending", "succeeded")


@dataclass(frozen=True)
class Ledger:
    paid: Decimal  # succeeded charges
    refunded: Decimal  # pending + succeeded refunds
    owed: Decimal  # the order total; nothing once cancelled
    card_refundable: Decimal  # card money that can still go back through Stripe
    # Commission the platform kept through Stripe application fees (net of fees returned with refunds).
    commission_collected: Decimal = ZERO

    @property
    def net(self) -> Decimal:
        return self.paid - self.refunded

    @property
    def balance_due(self) -> Decimal:
        return max(self.owed - self.net, ZERO)

    @property
    def overpaid(self) -> Decimal:
        return max(self.net - self.owed, ZERO)


def owed(order: Order) -> Decimal:
    return ZERO if order.status == CANCELLED else order.total


def _money(amount: Decimal) -> str:
    return f"${amount:.2f}"


def _rows(db: Session, order: Order) -> list[Payment]:
    db.flush()
    return list(
        db.execute(select(Payment).where(Payment.order_id == order.id).order_by(Payment.created_at)).scalars()
    )


def list_payments(db: Session, order: Order) -> list[Payment]:
    return _rows(db, order)


def _card_charges_with_remaining(rows: list[Payment]) -> list[tuple[Payment, Decimal]]:
    """Succeeded card charges, newest first, with how much of each is still refundable."""
    refunded: dict[uuid.UUID, Decimal] = {}
    for r in rows:
        if r.kind == "refund" and r.status in REFUND_COUNTED and r.parent_id is not None:
            refunded[r.parent_id] = refunded.get(r.parent_id, ZERO) + r.amount
    charges = [r for r in rows if r.kind == "charge" and r.method == "card" and r.status == "succeeded" and r.stripe_id]
    out = [(c, c.amount - refunded.get(c.id, ZERO)) for c in reversed(charges)]
    return [(c, remaining) for c, remaining in out if remaining > 0]


def ledger(db: Session, order: Order) -> Ledger:
    rows = _rows(db, order)
    paid = sum((r.amount for r in rows if r.kind == "charge" and r.status == "succeeded"), ZERO)
    refunded = sum((r.amount for r in rows if r.kind == "refund" and r.status in REFUND_COUNTED), ZERO)
    card_refundable = sum((remaining for _, remaining in _card_charges_with_remaining(rows)), ZERO)
    fees_taken = sum((r.application_fee or ZERO for r in rows if r.kind == "charge" and r.status == "succeeded"), ZERO)
    fees_returned = sum((r.application_fee or ZERO for r in rows if r.kind == "refund" and r.status in REFUND_COUNTED), ZERO)
    return Ledger(
        paid=paid,
        refunded=refunded,
        owed=owed(order),
        card_refundable=card_refundable,
        commission_collected=fees_taken - fees_returned,
    )


def application_fee_for(db: Session, order: Order, amount_due: Decimal) -> Decimal:
    """The platform commission to take from a card charge: whatever of the
    order's commission hasn't been collected through Stripe yet."""
    remaining = order.commission - ledger(db, order).commission_collected
    return min(max(remaining, ZERO), amount_due)


def _returned_fee(charge: Payment, refund_amount: Decimal) -> Decimal | None:
    """The share of a charge's application fee that Stripe returns with a refund
    (refunds are made with refund_application_fee, which is proportional)."""
    if not charge.application_fee or not charge.amount:
        return None
    return (charge.application_fee * refund_amount / charge.amount).quantize(Decimal("0.01"))


def net_paid_by_order(db: Session, order_ids: list[uuid.UUID]) -> dict[uuid.UUID, Decimal]:
    """Net amount paid per order, for order lists (one query)."""
    if not order_ids:
        return {}
    signed = case(
        ((Payment.kind == "charge") & (Payment.status == "succeeded"), Payment.amount),
        ((Payment.kind == "refund") & Payment.status.in_(REFUND_COUNTED), -Payment.amount),
        else_=ZERO,
    )
    rows = db.execute(
        select(Payment.order_id, func.sum(signed)).where(Payment.order_id.in_(order_ids)).group_by(Payment.order_id)
    ).all()
    return {order_id: Decimal(total or 0) for order_id, total in rows}


def commission_collected_by_order(db: Session, order_ids: list[uuid.UUID]) -> dict[uuid.UUID, Decimal]:
    """Commission taken through Stripe per order (application fees net of the
    part returned with refunds), for reports and invoices (one query)."""
    if not order_ids:
        return {}
    fee = func.coalesce(Payment.application_fee, 0)
    signed = case(
        ((Payment.kind == "charge") & (Payment.status == "succeeded"), fee),
        ((Payment.kind == "refund") & Payment.status.in_(REFUND_COUNTED), -fee),
        else_=0,
    )
    rows = db.execute(
        select(Payment.order_id, func.sum(signed)).where(Payment.order_id.in_(order_ids)).group_by(Payment.order_id)
    ).all()
    return {order_id: Decimal(total or 0) for order_id, total in rows}


def sync_payment_status(db: Session, order: Order) -> None:
    led = ledger(db, order)
    if led.net <= 0:
        status = "refunded" if led.refunded > 0 else "unpaid"
    elif led.net < led.owed:
        status = "partially_paid"
    else:
        status = "paid"
    if status == "paid" and order.paid_at is None:
        order.paid_at = utcnow_naive()
    order.payment_status = status


# ── Card payments (Stripe) ────────────────────────────────────────────────


def _by_stripe_id(db: Session, stripe_id: str) -> Payment | None:
    return db.execute(select(Payment).where(Payment.stripe_id == stripe_id)).scalar_one_or_none()


def open_card_charge(db: Session, order: Order) -> Payment | None:
    """The latest card charge the customer started but hasn't finished paying."""
    rows = [r for r in _rows(db, order) if r.kind == "charge" and r.method == "card" and r.status in ("pending", "failed")]
    return rows[-1] if rows else None


def record_card_charge_started(
    db: Session, order: Order, *, payment_intent_id: str, amount: Decimal, application_fee: Decimal
) -> None:
    db.add(
        Payment(
            order_id=order.id, kind="charge", method="card", amount=amount, status="pending",
            stripe_id=payment_intent_id, application_fee=application_fee,
        )
    )
    order.payment_ref = payment_intent_id


def receive_card_payment(
    db: Session,
    order: Order,
    *,
    payment_intent_id: str,
    amount: Decimal,
    application_fee: Decimal | None = None,
) -> None:
    """Stripe says a PaymentIntent succeeded (webhook). Idempotent."""
    row = _by_stripe_id(db, payment_intent_id)
    if row is not None and row.status == "succeeded":
        return
    if row is None:
        row = Payment(order_id=order.id, kind="charge", method="card", stripe_id=payment_intent_id)
        db.add(row)
    row.amount, row.status, row.failure_reason = amount, "succeeded", None
    row.stripe_fee = payment_service.fetch_stripe_fee(payment_intent_id)
    if application_fee is not None:
        row.application_fee = application_fee
    order.payment_ref = payment_intent_id
    log_event(db, order, actor=ACTOR_STRIPE, kind="payment_received", detail=f"{_money(amount)} paid by card")
    sync_payment_status(db, order)

    # Paid a moment after the order was cancelled: give the money straight back.
    if order.status == CANCELLED:
        try:
            refund(db, order, amount=min(amount, ledger(db, order).card_refundable), method="card", actor=ACTOR_STRIPE)
        except AppError:
            log_event(
                db, order, actor=ACTOR_STRIPE, kind="refund_failed",
                detail=f"Automatic refund of {_money(amount)} failed; refund it by hand",
            )


def update_card_charge(db: Session, *, payment_intent_id: str, status: str, failure_reason: str | None = None) -> None:
    """A PaymentIntent failed or was canceled (webhook). The customer may still
    retry the same PaymentIntent, so a later success overrides this."""
    row = _by_stripe_id(db, payment_intent_id)
    if row is None or row.status == "succeeded":
        return
    row.status = status
    row.failure_reason = (failure_reason or "")[:255] or None


def on_cancelled(db: Session, order: Order) -> None:
    """Stop card payments the customer started but hasn't finished."""
    for row in _rows(db, order):
        if row.kind == "charge" and row.method == "card" and row.status in ("pending", "failed") and row.stripe_id:
            if payment_service.cancel_payment_intent(row.stripe_id):
                row.status = "canceled"


# ── Refunds ───────────────────────────────────────────────────────────────


def _refund_status(stripe_status: str | None) -> str:
    return stripe_status if stripe_status in ("pending", "succeeded", "failed", "canceled") else "pending"


def refund(db: Session, order: Order, *, amount: Decimal, method: str, actor: str) -> Decimal:
    """Refund money paid on an order. Card refunds go back through Stripe,
    newest charge first; in-store refunds (cash back) are just recorded."""
    led = ledger(db, order)
    if amount <= 0 or amount > led.net:
        raise AppError(422, "refund_exceeds_paid", f"At most {_money(led.net)} can be refunded")

    if method == "in_store":
        db.add(Payment(order_id=order.id, kind="refund", method="in_store", amount=amount, status="succeeded"))
        log_event(db, order, actor=actor, kind="refund_issued", detail=f"{_money(amount)} refunded in store")
        sync_payment_status(db, order)
        return amount

    if amount > led.card_refundable:
        raise AppError(422, "refund_exceeds_card", f"At most {_money(led.card_refundable)} can go back to the card")
    done = ZERO
    for charge, remaining in _card_charges_with_remaining(_rows(db, order)):
        part = min(remaining, amount - done)
        try:
            result = payment_service.create_refund(charge.stripe_id, amount=part, order_id=str(order.id))
        except AppError:
            if done == 0:
                raise
            break  # keep what already went through; staff can refund the rest
        db.add(
            Payment(
                order_id=order.id, kind="refund", method="card", amount=part,
                status=_refund_status(result.status), stripe_id=result.refund_id, parent_id=charge.id,
                application_fee=_returned_fee(charge, part),
            )
        )
        done += part
        if done >= amount:
            break
    log_event(db, order, actor=actor, kind="refund_issued", detail=f"{_money(done)} refunded to card")
    sync_payment_status(db, order)
    return done


def update_refund(db: Session, *, refund_id: str, payment_intent_id: str | None, amount: Decimal, status: str) -> None:
    """Stripe reports a refund (webhook): ours changing state, or one made in the
    Stripe Dashboard that we haven't seen yet."""
    row = _by_stripe_id(db, refund_id)
    if row is None:
        charge = _by_stripe_id(db, payment_intent_id) if payment_intent_id else None
        if charge is None:
            return
        order = db.get(Order, charge.order_id)
        row = Payment(
            order_id=charge.order_id, kind="refund", method="card", amount=amount,
            status=_refund_status(status), stripe_id=refund_id, parent_id=charge.id,
            application_fee=_returned_fee(charge, amount),
        )
        db.add(row)
        if order is not None and row.status in REFUND_COUNTED:
            log_event(db, order, actor=ACTOR_STRIPE, kind="refund_issued", detail=f"{_money(amount)} refunded to card")
    else:
        order = db.get(Order, row.order_id)
        new_status = _refund_status(status)
        if new_status == row.status:
            return
        row.status = new_status
        if order is not None and new_status in ("failed", "canceled"):
            log_event(
                db, order, actor=ACTOR_STRIPE, kind="refund_failed",
                detail=f"Refund of {_money(row.amount)} {new_status}",
            )
    if order is not None:
        sync_payment_status(db, order)


def record_dispute(db: Session, *, dispute_id: str, payment_intent_id: str | None, amount: Decimal, status: str, reason: str | None) -> None:
    """A chargeback opened or closed (webhook). A lost dispute takes the money back."""
    charge = _by_stripe_id(db, payment_intent_id) if payment_intent_id else None
    order = db.get(Order, charge.order_id) if charge is not None else None
    if order is None:
        return
    if status in ("won", "lost"):
        log_event(db, order, actor=ACTOR_STRIPE, kind="dispute_closed", detail=f"Dispute of {_money(amount)} {status}")
        if status == "lost" and _by_stripe_id(db, dispute_id) is None:
            db.add(Payment(order_id=order.id, kind="refund", method="dispute", amount=amount, status="succeeded", stripe_id=dispute_id, parent_id=charge.id))
            sync_payment_status(db, order)
    else:
        log_event(
            db, order, actor=ACTOR_STRIPE, kind="dispute_opened",
            detail=f"Customer disputed {_money(amount)}" + (f" ({reason})" if reason else ""),
        )


# ── In-store payments ─────────────────────────────────────────────────────


def record_in_store_payment(db: Session, order: Order, *, amount: Decimal) -> None:
    """Staff took cash or card at the counter (e.g. the balance after an edit)."""
    led = ledger(db, order)
    if amount <= 0 or amount > led.balance_due:
        raise AppError(422, "amount_exceeds_balance", f"The balance due is {_money(led.balance_due)}")
    db.add(Payment(order_id=order.id, kind="charge", method="in_store", amount=amount, status="succeeded"))
    log_event(db, order, actor=ACTOR_STORE, kind="payment_received", detail=f"{_money(amount)} received in store")
    sync_payment_status(db, order)


# ── Telling the customer ──────────────────────────────────────────────────


@dataclass(frozen=True)
class CustomerNotice:
    message: str
    phone: str | None  # where a text or call would go; app orders have none yet
    pending: bool  # there are changes the customer hasn't been told about
    last_notified_at: datetime | None


_CHANGE_VERBS = {"item_added": "added", "item_removed": "removed", "item_updated": "changed"}


def customer_notice(db: Session, order: Order, store: Store) -> CustomerNotice:
    """The message for the customer about changes since they were last told."""
    events = list(
        db.execute(select(OrderEvent).where(OrderEvent.order_id == order.id).order_by(OrderEvent.created_at)).scalars()
    )
    last_notified_at = max((e.created_at for e in events if e.kind == "customer_notified"), default=None)
    since = [e for e in events if last_notified_at is None or e.created_at > last_notified_at]
    changes = [f"{_CHANGE_VERBS[e.kind]} {e.detail}" for e in since if e.kind in _CHANGE_VERBS]
    cancelled_now = any(e.kind == "status_changed" and e.detail.endswith(f"→ {CANCELLED}") for e in since)
    refunded_now = sum(
        (
            p.amount
            for p in _rows(db, order)
            if p.kind == "refund" and p.status in REFUND_COUNTED and (last_notified_at is None or p.created_at > last_notified_at)
        ),
        ZERO,
    )

    if order.status == CANCELLED:
        message = f"{store.name}: your order #{order.short_code} was cancelled."
    else:
        message = f"{store.name}: your order #{order.short_code} was updated"
        message += (": " + "; ".join(changes)) if changes else ""
        message += f". New total {_money(order.total)}."
        led = ledger(db, order)
        if led.net > 0 and led.balance_due > 0:
            where = "in the VoxEats app or at pickup" if order.user_id else "at pickup"
            message += f" Balance due: {_money(led.balance_due)}, payable {where}."
    if refunded_now > 0:
        message += f" A refund of {_money(refunded_now)} is on its way to you."
    if store.phone:
        message += f" Questions? Call {store.phone}."

    return CustomerNotice(
        message=message,
        phone=order.customer_phone,
        pending=bool(changes or cancelled_now or refunded_now > 0),
        last_notified_at=last_notified_at,
    )


def mark_customer_notified(db: Session, order: Order, *, method: str) -> None:
    detail = {"call": "Customer told by phone call", "sms": "Customer sent a text"}.get(method, "Customer told")
    log_event(db, order, actor=ACTOR_STORE, kind="customer_notified", detail=detail)
