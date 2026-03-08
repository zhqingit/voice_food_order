from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.menu_item import MenuItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.voice_session import VoiceSession
from app.services import order_service
from app.schemas.order.order import OrderCreate


"""Module for routing voice tool calls related to food ordering. Contains the VoiceToolContext dataclass for holding relevant context (DB session, store/user IDs, etc.) 
and the VoiceToolRouter class which implements the logic for handling tool calls like add_item, remove_item, get_summary, and checkout based on the current order state and menu data. 
The router uses the provided context to perform actions on the order and return results in a consistent format."""


@dataclass
class VoiceToolContext:
    db: Session
    store_id: uuid.UUID
    user_id: uuid.UUID | None
    channel: str = "voice"
    order_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None


class VoiceToolRouter:
    """Router for handling voice tool calls related to food ordering, using the provided context to perform actions on the order."""
    def __init__(self, context: VoiceToolContext) -> None:
        self._context = context

    # Helper method to find a menu item by name, ignoring case, within the current store's menu.
    def _find_menu_item_by_name(self, name: str) -> MenuItem | None:
        query = (
            select(MenuItem)
            .where(MenuItem.store_id == self._context.store_id)
            .where(MenuItem.name.ilike(name))
        )
        return self._context.db.execute(query).scalar_one_or_none()

    def _get_order(self) -> Order | None:
        """Retrieve the current order based on the context's order_id."""
        if self._context.order_id is None:
            return None
        return self._context.db.get(Order, self._context.order_id)

    def _ensure_order(self) -> Order:
        """Ensure there is a current order, creating a new draft order if necessary."""
        order = self._get_order()
        if order is not None:
            return order

        # If no order exists, create a new draft order for the current user and store.
        payload = OrderCreate(
            store_id=self._context.store_id,
            user_id=self._context.user_id,
            channel=self._context.channel,
            notes=None,
            items=[],
        )
        order = order_service.create_draft_order(self._context.db, payload=payload)
        self._context.order_id = order.id

        # Eagerly link the order to the voice session so the client can
        # fetch it even if the pipeline ends before the finally block runs.
        if self._context.session_id is not None:
            vs = self._context.db.get(VoiceSession, self._context.session_id)
            if vs is not None:
                vs.order_id = order.id

        self._context.db.commit()
        return order

    def _build_summary(self, order: Order) -> dict[str, Any]:
        """Build a summary of the current order, including item details and totals."""

        items = self._context.db.execute(select(OrderItem).where(OrderItem.order_id == order.id)).scalars().all()
        summary_items = []
        for item in items:
            menu_item = self._context.db.get(MenuItem, item.menu_item_id)
            name = menu_item.name if menu_item else "Unknown item"
            summary_items.append(
                {
                    "order_item_id": str(item.id),
                    "menu_item_id": str(item.menu_item_id),
                    "name": name,
                    "quantity": item.quantity,
                    "line_total": float(item.price_snapshot * item.quantity),
                }
            )
        return {
            "order_id": str(order.id),
            "status": order.status,
            "subtotal": float(order.subtotal),
            "tax": float(order.tax),
            "total": float(order.total),
            "items": summary_items,
        }

    def add_item(self, *, menu_item_id: uuid.UUID | None, item_name: str | None, quantity: int, size: str | None = None) -> dict[str, Any]:
        """Add an item to the current order."""
        if quantity <= 0:
            return {"ok": False, "message": "Quantity must be at least 1."}

        order = self._ensure_order()
        menu_item = None
        if menu_item_id is not None:
            menu_item = order_service.get_menu_item_for_store(
                self._context.db, store_id=self._context.store_id, item_id=menu_item_id
            )
        if menu_item is None and item_name:
            menu_item = self._find_menu_item_by_name(item_name)

        if menu_item is None:
            return {"ok": False, "message": "Menu item not found."}

        price = menu_item.price_for_size(size)
        order_service.create_order_item(self._context.db, order=order, menu_item=menu_item, quantity=quantity, price_override=price)
        self._context.db.flush()
        order_service.recalc_totals(self._context.db, order=order)
        self._context.db.commit()

        size_label = f" ({size})" if size else ""
        return {
            "ok": True,
            "message": f"Added {quantity} {menu_item.name}{size_label} at ${float(price):.2f} each.",
            "order": self._build_summary(order),
        }

    def remove_item(
        self,
        *,
        order_item_id: uuid.UUID | None,
        menu_item_id: uuid.UUID | None,
        item_name: str | None,
    ) -> dict[str, Any]:
        """Remove an item from the current order. Supports identifying the item to remove by order_item_id, menu_item_id, or item_name for flexibility."""
        order = self._get_order()
        if order is None:
            return {"ok": False, "message": "No active order."}

        item = None
        if order_item_id is not None:
            item = self._context.db.execute(
                select(OrderItem).where(OrderItem.order_id == order.id, OrderItem.id == order_item_id)
            ).scalar_one_or_none()
        if item is None and menu_item_id is not None:
            item = self._context.db.execute(
                select(OrderItem).where(OrderItem.order_id == order.id, OrderItem.menu_item_id == menu_item_id)
            ).scalar_one_or_none()
        if item is None and item_name:
            menu_item = self._find_menu_item_by_name(item_name)
            if menu_item is not None:
                item = self._context.db.execute(
                    select(OrderItem).where(OrderItem.order_id == order.id, OrderItem.menu_item_id == menu_item.id)
                ).scalar_one_or_none()

        if item is None:
            return {"ok": False, "message": "Item not found in the order."}

        self._context.db.delete(item)
        self._context.db.flush()
        order_service.recalc_totals(self._context.db, order=order)
        self._context.db.commit()

        return {
            "ok": True,
            "message": "Removed item.",
            "order": self._build_summary(order),
        }

    def get_summary(self) -> dict[str, Any]:
        """Get current order summary and totals."""
        order = self._get_order()
        if order is None:
            return {"ok": True, "message": "Order is empty.", "order": None}
        # Recalculate to ensure totals are fresh (autoflush is off).
        order_service.recalc_totals(self._context.db, order=order)
        self._context.db.flush()
        return {"ok": True, "message": "Order summary.", "order": self._build_summary(order)}

    def checkout(self) -> dict[str, Any]:
        """Finalize the order. This example simply changes the order status to 'submitted' and recalculates totals, 
        but in a real implementation this might involve additional steps such as confirming order details, handling payment, etc."""
        order = self._get_order()

        if order is None:
            return {"ok": False, "message": "Order is empty."}
        if order.status != "draft":
            return {"ok": False, "message": "Order is not editable."}

        order.status = "submitted"
        order_service.recalc_totals(self._context.db, order=order)
        self._context.db.commit()

        return {"ok": True, "message": "Order submitted.", "order": self._build_summary(order)}
