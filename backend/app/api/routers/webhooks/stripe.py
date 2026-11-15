"""Stripe webhook receiver.

Registered WITHOUT host policy — Stripe posts directly to the deployment host,
not one of the portal hosts. Signature verification (against the webhook
secret) is what authenticates the request.
"""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.order import Order
from app.models.store import Store
from app.services import order_payments, payment_service

log = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _field(obj: Any, key: str, default: Any = None) -> Any:
    """Read a key from a Stripe object or plain dict.

    The Stripe SDK's StripeObject does not expose a working ``.get()`` in this
    version (attribute lookup for ``get`` raises), so we use item access guarded
    against the missing-key KeyError. Works for both StripeObject and dict.
    """
    try:
        return obj[key]
    except (KeyError, TypeError):
        return default


def _dollars(cents: Any) -> Decimal:
    return (Decimal(int(cents or 0)) / 100).quantize(Decimal("0.01"))


def _order_from_metadata(db: Session, obj: Any) -> Order | None:
    order_id_raw = _field(_field(obj, "metadata") or {}, "order_id")
    if not order_id_raw:
        return None
    try:
        return db.get(Order, uuid.UUID(order_id_raw), with_for_update=True)
    except ValueError:
        return None


@router.post("/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    event = payment_service.verify_webhook(payload, signature)

    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "account.updated":
        account_id = _field(obj, "id")
        if account_id:
            store = db.execute(
                select(Store).where(Store.stripe_account_id == account_id)
            ).scalar_one_or_none()
            if store is not None:
                store.stripe_charges_enabled = bool(_field(obj, "charges_enabled"))
                db.add(store)
                db.commit()

    elif event_type == "payment_intent.succeeded":
        order = _order_from_metadata(db, obj)
        if order is not None and _field(obj, "id"):
            order_payments.receive_card_payment(
                db,
                order,
                payment_intent_id=_field(obj, "id"),
                amount=_dollars(_field(obj, "amount_received")),
                application_fee=(
                    _dollars(_field(obj, "application_fee_amount"))
                    if _field(obj, "application_fee_amount") is not None
                    else None
                ),
            )
            db.commit()

    elif event_type in ("payment_intent.payment_failed", "payment_intent.canceled"):
        error = _field(obj, "last_payment_error") or {}
        order_payments.update_card_charge(
            db,
            payment_intent_id=_field(obj, "id") or "",
            status="failed" if event_type.endswith("failed") else "canceled",
            failure_reason=_field(error, "message"),
        )
        db.commit()

    elif event_type in ("refund.created", "refund.updated", "refund.failed", "charge.refund.updated"):
        if _field(obj, "id"):
            order_payments.update_refund(
                db,
                refund_id=_field(obj, "id"),
                payment_intent_id=_field(obj, "payment_intent"),
                amount=_dollars(_field(obj, "amount")),
                status=_field(obj, "status") or "pending",
            )
            db.commit()

    elif event_type in ("charge.dispute.created", "charge.dispute.closed"):
        if _field(obj, "id"):
            order_payments.record_dispute(
                db,
                dispute_id=_field(obj, "id"),
                payment_intent_id=_field(obj, "payment_intent"),
                amount=_dollars(_field(obj, "amount")),
                status=_field(obj, "status") or "",
                reason=_field(obj, "reason"),
            )
            db.commit()

    return {"received": True}
