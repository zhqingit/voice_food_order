"""Stripe webhook receiver.

Registered WITHOUT host policy — Stripe posts directly to the deployment host,
not one of the portal hosts. Signature verification (against the webhook
secret) is what authenticates the request.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utcnow_naive
from app.db.session import get_db
from app.models.order import Order
from app.models.store import Store
from app.services import payment_service

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
        order_id_raw = _field(_field(obj, "metadata") or {}, "order_id")
        order = None
        if order_id_raw:
            try:
                order = db.get(Order, uuid.UUID(order_id_raw))
            except ValueError:
                order = None
        if order is not None and order.payment_status != "paid":
            order.payment_status = "paid"
            order.paid_at = utcnow_naive()
            order.payment_ref = _field(obj, "id") or order.payment_ref
            db.add(order)
            db.commit()

    return {"received": True}
