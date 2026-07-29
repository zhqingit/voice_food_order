from __future__ import annotations

import contextlib
import logging
import time
import uuid
from collections.abc import Generator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from app.core.time import utcnow_naive

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.menu_item import MenuItem
from app.models.menu_item_variant import MenuItemVariant
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.voice_session import VoiceSession
from app.models.store import Store
from app.services import delivery_service, menu_service, order_service
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
        variant_key: str,
        note: str | None,
        quantity: int,
    ) -> bool:
        now = time.monotonic()
        for k in list(self._recent_adds):
            if now - self._recent_adds[k] > self._DEDUP_WINDOW_SECONDS:
                del self._recent_adds[k]
        key = (str(menu_item_id), variant_key, note or "", int(quantity))
        return key in self._recent_adds

    def _record_add(
        self,
        menu_item_id: uuid.UUID,
        variant_key: str,
        note: str | None,
        quantity: int,
    ) -> None:
        key = (str(menu_item_id), variant_key, note or "", int(quantity))
        self._recent_adds[key] = time.monotonic()

    # ── private helpers (receive db as argument) ──────────────────────

    def _resolve_variant(
        self,
        db: Session,
        menu_item: MenuItem,
        variant: str | None,
        size: str | None,
    ) -> tuple[MenuItemVariant | None, str | None]:
        """Given a menu_item and an optional ``variant`` (new, free-form name
        like '2 Liter') or legacy ``size`` ('small'|'medium'|'large'), return
        either the resolved variant row or an error message string.

        Returns ``(variant_row, None)`` on success, or ``(None, error_msg)`` on
        failure. When the item has no variants at all, returns ``(None, None)``
        (not an error — the caller can use legacy size handling).
        """
        item_variants = list(menu_item.variants or [])

        if not item_variants:
            # Item has no variants defined. If the caller specified a variant
            # string, that's an error — we don't silently ignore it (that was
            # exactly the doom-loop bug with Coke).
            if variant and variant.strip():
                return None, (
                    f"{menu_item.name} comes in one size only — no '{variant}' option."
                )
            return None, None

        # Item HAS variants. Pick one.
        if variant and variant.strip():
            match = menu_service.find_variant_by_name(
                db, menu_item_id=menu_item.id, name=variant
            )
            if match is None:
                available = ", ".join(v.name for v in item_variants if v.availability)
                return None, (
                    f"{menu_item.name} doesn't have a '{variant}' option. "
                    f"Choose one of: {available}."
                )
            if not match.availability:
                return None, (
                    f"{menu_item.name} {match.name} is currently unavailable."
                )
            return match, None

        # No explicit variant — try the legacy size arg (map to variant name).
        if size and size.strip():
            size_norm = size.strip().lower()
            for v in item_variants:
                if v.name.lower() == size_norm:
                    if not v.availability:
                        return None, (
                            f"{menu_item.name} {v.name} is currently unavailable."
                        )
                    return v, None

        # Default: the variant flagged is_default, or the first available one.
        default = next((v for v in item_variants if v.is_default and v.availability), None)
        if default is not None:
            return default, None
        available_list = [v for v in item_variants if v.availability]
        if not available_list:
            return None, f"{menu_item.name} has no available options right now."
        # Caller provided nothing and no default — ask the bot to pick.
        names = ", ".join(v.name for v in available_list)
        return None, (
            f"{menu_item.name} comes in multiple options ({names}). "
            f"Please ask the customer which one."
        )

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
            if item.variant_name:
                item_data["variant"] = item.variant_name
            summary_items.append(item_data)
        result: dict[str, Any] = {
            "order_id": str(order.id),
            "short_code": order.short_code,
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

    def add_item(
        self,
        *,
        menu_item_id: uuid.UUID | None,
        item_name: str | None,
        quantity: int,
        variant: str | None = None,
        size: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        """Add an item to the current order.

        ``variant`` is the new, free-form variant name (e.g. "12 Oz Can",
        "2 Liter", "10 inch"). ``size`` is the legacy S/M/L arg — kept for
        back-compat; maps onto a variant row if one matches by name.
        """
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

            variant_row, variant_err = self._resolve_variant(db, menu_item, variant, size)
            if variant_err is not None:
                return {"ok": False, "message": variant_err}

            # Decide price + snapshot of variant name. If the item has variants,
            # variant_row is guaranteed non-None at this point (helper returned
            # an error otherwise). If not, fall back to legacy size-based price.
            if variant_row is not None:
                price = variant_row.price
                variant_name_snapshot: str | None = variant_row.name
                variant_key = variant_row.name.lower()
            else:
                price = menu_item.price_for_size(size)
                variant_name_snapshot = None
                variant_key = (size or "").lower()

            if self._is_duplicate_add(menu_item.id, variant_key, note, quantity):
                logger.warning(
                    "Duplicate add_item within %ss window: %s variant=%s qty=%d note=%s — skipping insert",
                    self._DEDUP_WINDOW_SECONDS,
                    menu_item.name,
                    variant_key or "-",
                    quantity,
                    note or "-",
                )
                return {
                    "ok": True,
                    "message": f"{menu_item.name} is already in the order.",
                    "order": self._build_summary(db, order),
                }

            oi = order_service.create_order_item(
                db,
                order=order,
                menu_item=menu_item,
                quantity=quantity,
                price_override=price,
                note=note,
            )
            if variant_name_snapshot is not None:
                oi.variant_name = variant_name_snapshot
            db.flush()
            order_service.recalc_totals(db, order=order)
            db.commit()
            self._record_add(menu_item.id, variant_key, note, quantity)

            variant_label = f" ({variant_name_snapshot})" if variant_name_snapshot else ""
            note_label = f" (note: {note})" if note else ""
            return {
                "ok": True,
                "message": (
                    f"Added {quantity} {menu_item.name}{variant_label} "
                    f"at ${float(price):.2f} each.{note_label}"
                ),
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

            # Tool-layer gate: delivery orders MUST have a verbal confirmation
            # (recorded by confirm_delivery_address) before checkout. This is
            # enforced server-side so the bot cannot skip the read-back step
            # even under prompt-instruction pressure.
            if order.fulfillment_type == "delivery":
                if order.delivery_confirmed_at is None:
                    return {
                        "ok": False,
                        "message": (
                            "Delivery address has not been confirmed by the customer yet. "
                            "Read the saved delivery_address back letter-by-letter and, when the customer says yes, "
                            "call confirm_delivery_address. Only then call checkout."
                        ),
                    }
                # Re-check delivery range at checkout — the address may have been
                # edited (or the store may have tightened its radius) after the
                # earlier set_fulfillment call.
                if order.delivery_address:
                    store = db.get(Store, self._context.store_id)
                    range_check = self._check_delivery_range(store, order.delivery_address)
                    if range_check is not None:
                        return range_check

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
        variant: str | None = None,
        size: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing order item's note, quantity, or variant.

        Honest about no-ops: if ``variant`` is passed but the menu_item has no
        variants configured, or the variant name doesn't exist, returns
        ``ok=False`` with an explanation so the bot can tell the customer
        instead of silently "succeeding" and re-trying in a loop.
        """
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

            # Variant/size change — resolve via the same helper as add_item
            # so the "single-price item has no sizes" case surfaces as an
            # honest error, not a silent no-op.
            if variant is not None or size is not None:
                menu_item = db.get(MenuItem, oi.menu_item_id)
                if menu_item is None:
                    return {"ok": False, "message": "Underlying menu item not found."}
                variant_row, variant_err = self._resolve_variant(
                    db, menu_item, variant, size
                )
                if variant_err is not None:
                    return {"ok": False, "message": variant_err}
                if variant_row is not None:
                    oi.variant_name = variant_row.name
                    oi.price_snapshot = variant_row.price
                    changes.append(f"option: {variant_row.name}")
                elif size is not None:
                    # Legacy size path (item has no variants at all)
                    oi.price_snapshot = menu_item.price_for_size(size)
                    changes.append(f"size: {size}")

            if not changes:
                return {
                    "ok": True,
                    "message": "Nothing to update.",
                    "order": self._build_summary(db, order),
                }

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

            if t == "delivery":
                store = db.get(Store, self._context.store_id)
                range_check = self._check_delivery_range(store, addr)
                if range_check is not None:
                    return range_check

            # If the address actually changed (including: switching to pickup,
            # or a different delivery address), drop any prior verbal
            # confirmation. The customer must reconfirm.
            prev_addr = (order.delivery_address or "").strip().lower()
            new_addr = (addr or "").strip().lower()
            if t != order.fulfillment_type or prev_addr != new_addr:
                order.delivery_confirmed_at = None

            order.fulfillment_type = t
            order.delivery_address = addr
            db.commit()

            if t == "pickup":
                msg = "Fulfillment set to pickup."
            else:
                msg = (
                    f"Fulfillment set to delivery to {addr}. "
                    "Address NOT yet confirmed by the customer — read it back letter-by-letter "
                    "and, only after the customer says yes, call confirm_delivery_address before checkout."
                )
            return {"ok": True, "message": msg, "order": self._build_summary(db, order)}

    def confirm_delivery_address(self) -> dict[str, Any]:
        """Record that the customer verbally confirmed the saved delivery address.

        Required before checkout for delivery orders. The bot must read the
        saved address back and wait for the customer's "yes" before calling
        this. Any subsequent change to the address (via set_fulfillment or the
        client UI) clears this flag and requires another confirmation.
        """
        with self._context.db_factory() as db:
            order = self._get_order(db)
            if order is None:
                return {"ok": False, "message": "No active order."}
            if order.status != "draft":
                return {"ok": False, "message": "Order is not editable."}
            if order.fulfillment_type != "delivery":
                return {
                    "ok": False,
                    "message": "Confirmation is only needed for delivery orders.",
                }
            if not (order.delivery_address or "").strip():
                return {
                    "ok": False,
                    "message": "No delivery address has been captured yet. Ask the customer for one and call set_fulfillment first.",
                }
            order.delivery_confirmed_at = utcnow_naive()
            db.commit()
            return {
                "ok": True,
                "message": f"Delivery address confirmed: {order.delivery_address}.",
                "order": self._build_summary(db, order),
            }

    def _check_delivery_range(
        self, store: Store | None, delivery_address: str
    ) -> dict[str, Any] | None:
        """Run the range check and return a tool-failure dict on rejection.

        Returns None when the address is in range (callers proceed). The
        returned failure dict mirrors the documented voice contract: a
        structured `reason` so the LLM can phrase a natural response."""
        if store is None:
            return {
                "ok": False,
                "reason": delivery_service.REASON_STORE_NO_LOCATION,
                "message": "This store hasn't configured a delivery area yet.",
            }
        in_range, distance_km, reason = delivery_service.is_within_delivery_range(
            store, delivery_address
        )
        if in_range:
            return None
        if reason == delivery_service.REASON_OUT_OF_RANGE:
            return {
                "ok": False,
                "reason": reason,
                "distance_km": round(distance_km, 2) if distance_km is not None else None,
                "max_km": float(store.delivery_radius_km) if store.delivery_radius_km else None,
                "message": (
                    f"That address is about {distance_km:.1f} km away, but we only "
                    f"deliver within {store.delivery_radius_km:.1f} km. Would you like "
                    "pickup instead, or a different address?"
                ),
            }
        if reason == delivery_service.REASON_GEOCODE_FAILED:
            return {
                "ok": False,
                "reason": reason,
                "message": "I couldn't locate that address. Could you say it again, or include the postcode?",
            }
        if reason == delivery_service.REASON_STORE_NO_LOCATION:
            return {
                "ok": False,
                "reason": reason,
                "message": "This store hasn't set a delivery location yet. Would you like pickup instead?",
            }
        if reason == delivery_service.REASON_STORE_NO_RADIUS:
            return {
                "ok": False,
                "reason": reason,
                "message": "This store hasn't set a delivery radius yet. Would you like pickup instead?",
            }
        return {
            "ok": False,
            "reason": reason,
            "message": "I couldn't confirm that delivery address. Would you like pickup instead?",
        }
