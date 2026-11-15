"""Stripe Connect (Express) payment service.

The single module that touches the Stripe SDK. The platform's secret key drives
every call; each store is a connected Express account referenced by its acct_
id (stores.stripe_account_id).

Customer charges use **destination charges**: the platform creates the
PaymentIntent, keeps `application_fee_amount` (the commission), and routes the
remainder to the store's connected account. Stripe then pays the store out to
their bank on their own schedule.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Callable

import stripe

from app.core.config import settings
from app.core.errors import AppError
from app.models.order import Order
from app.models.store import Store

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class AccountStatus:
    """Snapshot of a connected account's readiness, fetched live from Stripe."""

    charges_enabled: bool
    details_submitted: bool
    payouts_enabled: bool


@dataclass(frozen=True)
class PaymentIntentResult:
    client_secret: str
    payment_intent_id: str


@dataclass(frozen=True)
class PaymentIntentState:
    status: str
    client_secret: str
    amount: int  # cents


@dataclass(frozen=True)
class RefundResult:
    refund_id: str
    status: str  # pending | succeeded | failed | canceled | requires_action


def _ensure_configured() -> None:
    if not settings.stripe_secret_key:
        raise AppError(500, "stripe_not_configured", "Stripe is not configured.")
    stripe.api_key = settings.stripe_secret_key


def _call(action: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Run a Stripe SDK call, translating provider errors into AppError."""
    _ensure_configured()
    try:
        return fn(*args, **kwargs)
    except stripe.error.StripeError as exc:
        log.warning("payment_service.%s stripe error: %s", action, exc)
        raise AppError(502, "stripe_error", "Payment provider error.") from exc


def to_cents(amount: Decimal) -> int:
    """Convert a dollar Decimal (2dp) to an integer cent amount for Stripe."""
    return int((amount * 100).to_integral_value(rounding=ROUND_HALF_UP))


# ── Connect onboarding ────────────────────────────────────────────────────


def create_express_account(store: Store) -> str:
    """Create a Stripe Express connected account for a store; return its acct_ id."""
    acct = _call(
        "create_express_account",
        stripe.Account.create,
        type="express",
        country="US",
        email=store.email,
        capabilities={
            "card_payments": {"requested": True},
            "transfers": {"requested": True},
        },
        business_profile={"name": store.name},
        metadata={"store_id": str(store.id)},
    )
    return acct.id


def create_account_link(account_id: str, *, refresh_url: str, return_url: str) -> str:
    """Create a one-time Stripe-hosted onboarding URL for a connected account."""
    link = _call(
        "create_account_link",
        stripe.AccountLink.create,
        account=account_id,
        refresh_url=refresh_url,
        return_url=return_url,
        type="account_onboarding",
    )
    return link.url


def fetch_account_status(account_id: str) -> AccountStatus:
    """Retrieve a connected account's current readiness from Stripe."""
    acct = _call("fetch_account_status", stripe.Account.retrieve, account_id)
    return AccountStatus(
        charges_enabled=bool(acct.charges_enabled),
        details_submitted=bool(acct.details_submitted),
        payouts_enabled=bool(acct.payouts_enabled),
    )


# ── Charging the customer ─────────────────────────────────────────────────


def create_payment_intent(
    order: Order, store: Store, *, amount_due: Decimal, application_fee: Decimal
) -> PaymentIntentResult:
    """Create a destination-charge PaymentIntent for an order.

    Charges the customer `amount_due` (the order total, or the balance still
    owed after staff raised the total), keeps `application_fee` (the platform
    commission not collected yet, see order_payments.application_fee_for) and
    routes the rest to the store's connected account. Callers must confirm the store is payment-ready first; this guards
    defensively and refuses otherwise.
    """
    if not store.stripe_account_id or not store.stripe_charges_enabled:
        raise AppError(409, "store_not_payment_ready", "This store cannot accept online payments yet.")

    amount = to_cents(amount_due)
    if amount <= 0:
        raise AppError(400, "invalid_amount", "Order total must be positive to charge.")

    fee = min(max(to_cents(application_fee), 0), amount)
    intent = _call(
        "create_payment_intent",
        stripe.PaymentIntent.create,
        amount=amount,
        currency="usd",
        automatic_payment_methods={"enabled": True},
        application_fee_amount=fee,
        transfer_data={"destination": store.stripe_account_id},
        metadata={"order_id": str(order.id), "store_id": str(store.id)},
    )
    return PaymentIntentResult(client_secret=intent.client_secret, payment_intent_id=intent.id)


def retrieve_payment_intent(payment_intent_id: str) -> PaymentIntentState:
    intent = _call("retrieve_payment_intent", stripe.PaymentIntent.retrieve, payment_intent_id)
    return PaymentIntentState(status=intent.status, client_secret=intent.client_secret, amount=int(intent.amount))


def fetch_stripe_fee(payment_intent_id: str) -> Decimal | None:
    """Stripe's processing fee on a succeeded charge, in dollars (the platform
    pays it on destination charges). Best-effort: None if it can't be read."""
    try:
        intent = _call(
            "fetch_stripe_fee",
            stripe.PaymentIntent.retrieve,
            payment_intent_id,
            expand=["latest_charge.balance_transaction"],
        )
        txn = intent.latest_charge.balance_transaction
        return (Decimal(int(txn.fee)) / 100).quantize(Decimal("0.01"))
    except Exception:  # noqa: BLE001 - reporting data only; never fail the webhook
        log.warning("payment_service.fetch_stripe_fee failed for %s", payment_intent_id, exc_info=True)
        return None


def cancel_payment_intent(payment_intent_id: str) -> bool:
    """Cancel a PaymentIntent the customer hasn't paid. False if Stripe refused
    (e.g. it succeeded a moment ago; the webhook then handles the payment)."""
    try:
        _call("cancel_payment_intent", stripe.PaymentIntent.cancel, payment_intent_id)
        return True
    except AppError:
        return False


def create_refund(payment_intent_id: str, *, amount: Decimal, order_id: str) -> RefundResult:
    """Refund part or all of a destination charge.

    The money is pulled back from the store's connected account
    (reverse_transfer) and the platform commission on it is returned too.
    """
    refund = _call(
        "create_refund",
        stripe.Refund.create,
        payment_intent=payment_intent_id,
        amount=to_cents(amount),
        reverse_transfer=True,
        refund_application_fee=True,
        metadata={"order_id": order_id},
    )
    return RefundResult(refund_id=refund.id, status=refund.status)


# ── Webhook ───────────────────────────────────────────────────────────────


def verify_webhook(payload: bytes, signature: str) -> stripe.Event:
    """Verify a Stripe webhook signature and return the parsed event.

    STRIPE_WEBHOOK_SECRET may hold several comma-separated secrets: the
    platform ("Your account") endpoint and the Connect ("Connected accounts")
    endpoint each have their own signing secret.
    """
    secrets = [s.strip() for s in (settings.stripe_webhook_secret or "").split(",") if s.strip()]
    if not secrets:
        raise AppError(500, "stripe_not_configured", "Stripe webhook secret is not configured.")
    last_exc: Exception | None = None
    for secret in secrets:
        try:
            return stripe.Webhook.construct_event(payload, signature, secret)
        except (ValueError, stripe.error.SignatureVerificationError) as exc:
            last_exc = exc
    log.warning("payment_service.verify_webhook invalid signature: %s", last_exc)
    raise AppError(400, "invalid_webhook", "Invalid webhook signature.") from last_exc
