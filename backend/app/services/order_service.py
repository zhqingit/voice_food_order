from __future__ import annotations

import secrets
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.menu_item import MenuItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.store import Store
from app.schemas.order.order import OrderCreate


# Voice-friendly alphabet — no I, L, O, 0, 1 (sound or look ambiguous when
# spoken back to a customer). Keep in sync with the Alembic migration
# `0023_add_order_short_code` which uses the same alphabet for backfill.
_SHORT_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXY23456789"
_SHORT_CODE_LEN = 5
_SHORT_CODE_TRIES = 20


def _today_in_store_tz(store: Store) -> date:
    tz_name = (store.timezone or "").strip()
    if tz_name:
        try:
            tz = ZoneInfo(tz_name)
        except ZoneInfoNotFoundError:
            tz = timezone.utc
    else:
        tz = timezone.utc
    return datetime.now(tz=timezone.utc).astimezone(tz).date()


def _generate_short_code() -> str:
    return "".join(secrets.choice(_SHORT_CODE_ALPHABET) for _ in range(_SHORT_CODE_LEN))


def _assign_short_code(db: Session, *, order: Order, store: Store) -> None:
    """Assign a per-day per-store unique short code to ``order``.

    Picks a random code and checks the (store_id, code_day, short_code) unique
    index won't collide. With 30^5 ≈ 24M combos per (store, day), collisions
    are vanishingly rare; we retry a few times for safety. Caller flushes/
    commits — we set both columns on the in-memory order object.
    """
    code_day = _today_in_store_tz(store)
    for _ in range(_SHORT_CODE_TRIES):
        candidate = _generate_short_code()
        exists = db.execute(
            select(Order.id)
            .where(Order.store_id == store.id)
            .where(Order.code_day == code_day)
            .where(Order.short_code == candidate)
            .limit(1)
        ).first()
        if exists is None:
            order.short_code = candidate
            order.code_day = code_day
            return
    # 24M-slot bucket exhausted somehow — extend with a hex byte so the
    # migration always succeeds. Should be impossible in practice.
    order.short_code = _generate_short_code() + secrets.token_hex(1).upper()
    order.code_day = code_day


def get_menu_item_for_store(db: Session, *, store_id: uuid.UUID, item_id: uuid.UUID) -> MenuItem | None:
    return db.execute(
        select(MenuItem)
        .where(MenuItem.store_id == store_id)
        .where(MenuItem.id == item_id)
    ).scalar_one_or_none()


def create_draft_order(db: Session, *, payload: OrderCreate) -> Order:
    store = db.get(Store, payload.store_id)
    if store is None:
        # Caller is expected to have validated this earlier; raise loudly if
        # not so the FK constraint failure isn't the first hint.
        raise ValueError(f"create_draft_order: store {payload.store_id} not found")
    order = Order(
        store_id=payload.store_id,
        user_id=payload.user_id,
        status="draft",
        channel=payload.channel,
        notes=payload.notes,
        subtotal=Decimal("0.00"),
        tax=Decimal("0.00"),
        total=Decimal("0.00"),
    )
    _assign_short_code(db, order=order, store=store)
    db.add(order)
    db.flush()

    if payload.items:
        for item in payload.items:
            menu_item = get_menu_item_for_store(db, store_id=payload.store_id, item_id=item.menu_item_id)
            if menu_item is None:
                continue
            create_order_item(db, order=order, menu_item=menu_item, quantity=item.quantity)
        recalc_totals(db, order=order)

    return order


def create_order_item(db: Session, *, order: Order, menu_item: MenuItem, quantity: int, price_override: Decimal | None = None, note: str | None = None) -> OrderItem:
    item = OrderItem(
        order_id=order.id,
        menu_item_id=menu_item.id,
        quantity=quantity,
        price_snapshot=price_override if price_override is not None else menu_item.price,
        note=note,
    )
    db.add(item)
    return item


def remove_order_item(db: Session, *, order: Order, item_id: uuid.UUID) -> None:
    item = db.execute(
        select(OrderItem).where(OrderItem.order_id == order.id).where(OrderItem.id == item_id)
    ).scalar_one_or_none()
    if item is None:
        return
    db.delete(item)


def recalc_totals(db: Session, *, order: Order, tax_rate: Decimal | None = None) -> Order:
    items = db.execute(select(OrderItem).where(OrderItem.order_id == order.id)).scalars().all()
    subtotal = sum((item.price_snapshot * item.quantity for item in items), Decimal("0.00"))

    if tax_rate is None:
        # Look up the store's tax rate.
        from app.models.store import Store
        store = db.get(Store, order.store_id)
        tax_rate = store.tax_rate if store else Decimal("0.0000")

    tax = (subtotal * tax_rate).quantize(Decimal("0.01"))
    total = subtotal + tax

    order.subtotal = subtotal
    order.tax = tax
    order.total = total
    return order
