from __future__ import annotations

import contextlib
import logging
import time
import uuid
from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.menu_item import MenuItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.voice_session import VoiceSession
from app.services import order_service
from app.schemas.order.order import OrderCreate

logger = logging.getLogger(__name__)


@dataclass
class VoiceToolContext:
    db_factory: Callable[[], contextlib.AbstractContextManager[Session]]
    store_id: uuid.UUID
    user_id: uuid.UUID | None
    channel: str = "voice"
    order_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None


class VoiceToolRouter:
    """Router for handling voice tool calls related to food ordering."""

    # Window during which an identical add_item (same menu item + size + note +
    # quantity) is treated as a duplicate retry rather than a new line item.
    # Guards against the pipecat race where a function call is cancelled
    # mid-flight (DB write completes but result never reaches Gemini), and
    # Gemini retries the same tool call several seconds later.
    _DEDUP_WINDOW_SECONDS = 30.0

    def __init__(self, context: VoiceToolContext) -> None:
        self._context = context
        self._recent_adds: dict[tuple, float] = {}

    def _is_duplicate_add(
        self,
        menu_item_id: uuid.UUID,
        size: str | None,
        note: str | None,
        quantity: int,
    ) -> bool:
        now = time.monotonic()
        for k in list(self._recent_adds):
            if now - self._recent_adds[k] > self._DEDUP_WINDOW_SECONDS:
                del self._recent_adds[k]
        key = (str(menu_item_id), size or "", note or "", int(quantity))
        return key in self._recent_adds

    def _record_add(
        self,
        menu_item_id: uuid.UUID,
        size: str | None,
        note: str | None,
        quantity: int,
    ) -> None:
        key = (str(menu_item_id), size or "", note or "", int(quantity))
        self._recent_adds[key] = time.monotonic()

    # ── private helpers (receive db as argument) ──────────────────────

    def _find_menu_item_by_name(self, db: Session, name: str) -> MenuItem | None:
        from sqlalchemy import or_

        # Try exact match first (name or alias).
        query = (
            select(MenuItem)
            .where(MenuItem.store_id == self._context.store_id)
            .where(or_(MenuItem.name.ilike(name), MenuItem.alias_name.ilike(name)))
            .limit(1)
        )
        item = db.execute(query).scalar_one_or_none()
        if item is not None:
            return item

        # Fuzzy: check if menu item name is contained in the search string
        # (handles LLM passing "Beijing Beef (北京牛)" for item named "Beijing Beef").
        rows = db.execute(
            select(MenuItem).where(MenuItem.store_id == self._context.store_id)
        ).scalars().all()
        name_lower = name.lower()
        for row in rows:
            if row.name and row.name.lower() in name_lower:
                return row
            if row.alias_name and row.alias_name.lower() in name_lower:
                return row
        return None

    def _get_order(self, db: Session) -> Order | None:
        if self._context.order_id is None:
            return None
        return db.get(Order, self._context.order_id)

    def _ensure_order(self, db: Session) -> Order:
        order = self._get_order(db)
        if order is not None:
            return order

        payload = OrderCreate(
            store_id=self._context.store_id,
            user_id=self._context.user_id,
            channel=self._context.channel,
            notes=None,
            items=[],
        )
        order = order_service.create_draft_order(db, payload=payload)
        self._context.order_id = order.id

        if self._context.session_id is not None:
            vs = db.get(VoiceSession, self._context.session_id)
            if vs is not None:
                vs.order_id = order.id

        db.commit()
        return order

    def _build_summary(self, db: Session, order: Order) -> dict[str, Any]:
        items = db.execute(select(OrderItem).where(OrderItem.order_id == order.id)).scalars().all()
        summary_items = []
        for item in items:
            menu_item = db.get(MenuItem, item.menu_item_id)
            name = menu_item.name if menu_item else "Unknown item"
            item_data: dict[str, Any] = {
                "order_item_id": str(item.id),
                "menu_item_id": str(item.menu_item_id),
                "name": name,
                "quantity": item.quantity,
                "line_total": float(item.price_snapshot * item.quantity),
            }
            if item.note:
                item_data["note"] = item.note
            summary_items.append(item_data)
        result: dict[str, Any] = {
            "order_id": str(order.id),
            "status": order.status,
            "subtotal": float(order.subtotal),
            "tax": float(order.tax),
            "total": float(order.total),
            "items": summary_items,
        }
        if order.customer_name:
            result["customer_name"] = order.customer_name
        if order.notes:
            result["notes"] = order.notes
        if order.fulfillment_type:
            result["fulfillment_type"] = order.fulfillment_type
        if order.delivery_address:
            result["delivery_address"] = order.delivery_address
        return result

    # ── public methods (each opens its own short-lived session) ───────

    def add_item(self, *, menu_item_id: uuid.UUID | None, item_name: str | None, quantity: int, size: str | None = None, note: str | None = None) -> dict[str, Any]:
        if quantity <= 0:
            return {"ok": False, "message": "Quantity must be at least 1."}

        with self._context.db_factory() as db:
            order = self._ensure_order(db)
            menu_item = None
            if menu_item_id is not None:
                menu_item = order_service.get_menu_item_for_store(
                    db, store_id=self._context.store_id, item_id=menu_item_id
                )
            if menu_item is None and item_name:
                menu_item = self._find_menu_item_by_name(db, item_name)

            if menu_item is None:
                return {"ok": False, "message": "Menu item not found."}

            if not menu_item.availability:
                return {
                    "ok": False,
                    "message": f"Sorry, {menu_item.name} is currently unavailable.",
                }

            if self._is_duplicate_add(menu_item.id, size, note, quantity):
                logger.warning(
                    "Duplicate add_item within %ss window: %s size=%s qty=%d note=%s — skipping insert",
                    self._DEDUP_WINDOW_SECONDS,
                    menu_item.name,
                    size or "-",
                    quantity,
                    note or "-",
                )
                return {
                    "ok": True,
                    "message": f"{menu_item.name} is already in the order.",
                    "order": self._build_summary(db, order),
                }

            price = menu_item.price_for_size(size)
            order_service.create_order_item(db, order=order, menu_item=menu_item, quantity=quantity, price_override=price, note=note)
            db.flush()
            order_service.recalc_totals(db, order=order)
            db.commit()
            self._record_add(menu_item.id, size, note, quantity)

            size_label = f" ({size})" if size else ""
            note_label = f" (note: {note})" if note else ""
            return {
                "ok": True,
                "message": f"Added {quantity} {menu_item.name}{size_label} at ${float(price):.2f} each.{note_label}",
                "order": self._build_summary(db, order),
            }

    def remove_item(
        self,
        *,
        order_item_id: uuid.UUID | None,
        menu_item_id: uuid.UUID | None,
        item_name: str | None,
    ) -> dict[str, Any]:
        with self._context.db_factory() as db:
            order = self._get_order(db)
            if order is None:
                return {"ok": False, "message": "No active order."}

            item = None
            if order_item_id is not None:
                item = db.execute(
                    select(OrderItem).where(OrderItem.order_id == order.id, OrderItem.id == order_item_id)
                ).scalar_one_or_none()
            if item is None and menu_item_id is not None:
                item = db.execute(
                    select(OrderItem).where(OrderItem.order_id == order.id, OrderItem.menu_item_id == menu_item_id).limit(1)
                ).scalar_one_or_none()
            if item is None and item_name:
                menu_item = self._find_menu_item_by_name(db, item_name)
                if menu_item is not None:
                    item = db.execute(
                        select(OrderItem).where(OrderItem.order_id == order.id, OrderItem.menu_item_id == menu_item.id).limit(1)
                    ).scalar_one_or_none()

            if item is None:
                return {"ok": False, "message": "Item not found in the order."}

            db.delete(item)
            db.flush()
            order_service.recalc_totals(db, order=order)
            db.commit()

            return {
                "ok": True,
                "message": "Removed item.",
                "order": self._build_summary(db, order),
            }

    def get_summary(self) -> dict[str, Any]:
        with self._context.db_factory() as db:
            order = self._get_order(db)
            if order is None:
                return {"ok": True, "message": "Order is empty.", "order": None}
            order_service.recalc_totals(db, order=order)
            db.flush()
            return {"ok": True, "message": "Order summary.", "order": self._build_summary(db, order)}

    def checkout(self, *, customer_name: str | None = None) -> dict[str, Any]:
        with self._context.db_factory() as db:
            order = self._get_order(db)

            if order is None:
                return {"ok": False, "message": "Order is empty."}
            if order.status != "draft":
                return {"ok": False, "message": "Order is not editable."}

            if customer_name:
                order.customer_name = customer_name
            order.status = "submitted"
            order_service.recalc_totals(db, order=order)
            db.commit()

            return {"ok": True, "message": "Order submitted.", "order": self._build_summary(db, order)}

    def update_item(
        self,
        *,
        order_item_id: uuid.UUID | None = None,
        item_name: str | None = None,
        note: str | None = None,
        quantity: int | None = None,
        size: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing order item's note, quantity, or size."""
        with self._context.db_factory() as db:
            order = self._get_order(db)
            if order is None:
                return {"ok": False, "message": "No active order."}

            # Find the order item
            oi = None
            if order_item_id is not None:
                oi = db.execute(
                    select(OrderItem).where(OrderItem.order_id == order.id, OrderItem.id == order_item_id)
                ).scalar_one_or_none()
            if oi is None and item_name:
                menu_item = self._find_menu_item_by_name(db, item_name)
                if menu_item is not None:
                    oi = db.execute(
                        select(OrderItem).where(OrderItem.order_id == order.id, OrderItem.menu_item_id == menu_item.id).limit(1)
                    ).scalar_one_or_none()
            if oi is None:
                return {"ok": False, "message": "Item not found in the order."}

            changes: list[str] = []
            if note is not None:
                oi.note = note
                changes.append(f"note: {note}")
            if quantity is not None and quantity > 0:
                oi.quantity = quantity
                changes.append(f"quantity: {quantity}")
            if size is not None:
                menu_item = db.get(MenuItem, oi.menu_item_id)
                if menu_item:
                    oi.price_snapshot = menu_item.price_for_size(size)
                    changes.append(f"size: {size}")

            order_service.recalc_totals(db, order=order)
            db.commit()

            menu_item = db.get(MenuItem, oi.menu_item_id)
            name = menu_item.name if menu_item else "item"
            return {
                "ok": True,
                "message": f"Updated {name}: {', '.join(changes)}.",
                "order": self._build_summary(db, order),
            }

    def update_item_note(self, *, order_item_id: uuid.UUID, note: str) -> dict[str, Any]:
        """Update the note on a specific order item (used by background note verification)."""
        return self.update_item(order_item_id=order_item_id, note=note)

    def set_order_note(self, *, note: str) -> dict[str, Any]:
        with self._context.db_factory() as db:
            order = self._get_order(db)
            if order is None:
                return {"ok": False, "message": "No active order."}
            if order.status != "draft":
                return {"ok": False, "message": "Order is not editable."}

            order.notes = note
            db.commit()

            return {"ok": True, "message": f"Order note set: {note}", "order": self._build_summary(db, order)}

    def set_fulfillment(self, *, type: str, delivery_address: str | None = None) -> dict[str, Any]:
        t = (type or "").strip().lower()
        if t not in ("pickup", "delivery"):
            return {"ok": False, "message": "type must be 'pickup' or 'delivery'."}
        if t == "delivery":
            addr = (delivery_address or "").strip()
            if not addr:
                return {"ok": False, "message": "Delivery address is required for delivery orders."}
        else:
            addr = None

        with self._context.db_factory() as db:
            order = self._ensure_order(db)
            if order.status != "draft":
                return {"ok": False, "message": "Order is not editable."}

            order.fulfillment_type = t
            order.delivery_address = addr
            db.commit()

            if t == "pickup":
                msg = "Fulfillment set to pickup."
            else:
                msg = f"Fulfillment set to delivery to {addr}."
            return {"ok": True, "message": msg, "order": self._build_summary(db, order)}
