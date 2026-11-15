"""Platform commission on orders.

The rate depends on the channel the order came in on (app or phone): each
store may override the platform default for either. It is charged on the
pre-tax subtotal, and locked on the order when the order is created, so a later
rate change never alters past orders.

For orders paid online, the commission is taken from each Stripe charge as the
application fee. Whatever wasn't collected that way (orders paid at the store)
is billed to the store monthly.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.core.config import settings
from app.models.order import Order
from app.models.store import Store

PHONE_CHANNEL = "phone"


def is_phone(channel: str) -> bool:
    return channel == PHONE_CHANNEL


def default_bps(channel: str) -> int:
    return settings.commission_phone_bps if is_phone(channel) else settings.commission_app_bps


def resolve_bps(store: Store, channel: str) -> int:
    """This store's rate for orders on this channel: its override, else the platform default."""
    override = store.commission_phone_bps if is_phone(channel) else store.commission_app_bps
    return max(0, int(override if override is not None else default_bps(channel)))


def amount(subtotal: Decimal, bps: int) -> Decimal:
    return (subtotal * bps / Decimal(10000)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def apply(order: Order, store: Store | None) -> None:
    """Lock the rate on first use and recompute the commission from the subtotal."""
    if order.commission_bps is None:
        if store is None:
            return
        order.commission_bps = resolve_bps(store, order.channel)
    order.commission = amount(order.subtotal or Decimal("0.00"), order.commission_bps)
