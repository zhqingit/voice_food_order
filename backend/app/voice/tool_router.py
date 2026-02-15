from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.menu import Menu
from app.models.menu_item import MenuItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.services import order_service
from app.schemas.order.order import OrderCreate


@dataclass
class VoiceToolContext:
    db: Session
    store_id: uuid.UUID
    user_id: uuid.UUID | None
    channel: str = "voice"
    order_id: uuid.UUID | None = None


class VoiceToolRouter:
    def __init__(self, context: VoiceToolContext) -> None:
        self._context = context

    def _find_menu_item_by_name(self, name: str) -> MenuItem | None:
        query = (
            select(MenuItem)
            .join(Menu, Menu.id == MenuItem.menu_id)
            .where(Menu.store_id == self._context.store_id)
            .where(MenuItem.name.ilike(name))
        )
        return self._context.db.execute(query).scalar_one_or_none()

    def _get_order(self) -> Order | None:
        if self._context.order_id is None:
            return None
        return self._context.db.get(Order, self._context.order_id)

    def _ensure_order(self) -> Order:
        order = self._get_order()
        if order is not None:
            return order

        payload = OrderCreate(
            store_id=self._context.store_id,
            user_id=self._context.user_id,
            channel=self._context.channel,
            notes=None,
            items=[],
        )
        order = order_service.create_draft_order(self._context.db, payload=payload)
        self._context.db.flush()
        self._context.order_id = order.id
        return order

    def _build_summary(self, order: Order) -> dict[str, Any]:
        items = self._context.db.execute(select(OrderItem).where(OrderItem.order_id == order.id)).scalars().all()
        summary_items = []
        for item in items:
            menu_item = self._context.db.get(MenuItem, item.menu_item_id)
            name = menu_item.name if menu_item else "Unknown item"
            summary_items.append(
                {
                    "order_item_id": item.id,
                    "menu_item_id": item.menu_item_id,
                    "name": name,
                    "quantity": item.quantity,
                    "line_total": item.price_snapshot * item.quantity,
                }
            )
        return {
            "order_id": order.id,
            "status": order.status,
            "subtotal": order.subtotal,
            "tax": order.tax,
            "total": order.total,
            "items": summary_items,
        }

    def add_item(self, *, menu_item_id: uuid.UUID | None, item_name: str | None, quantity: int) -> dict[str, Any]:
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

        order_service.create_order_item(self._context.db, order=order, menu_item=menu_item, quantity=quantity)
        order_service.recalc_totals(self._context.db, order=order)
        self._context.db.flush()

        return {
            "ok": True,
            "message": f"Added {quantity} {menu_item.name}.",
            "order": self._build_summary(order),
        }

    def remove_item(
        self,
        *,
        order_item_id: uuid.UUID | None,
        menu_item_id: uuid.UUID | None,
        item_name: str | None,
    ) -> dict[str, Any]:
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
        order_service.recalc_totals(self._context.db, order=order)
        self._context.db.flush()

        return {
            "ok": True,
            "message": "Removed item.",
            "order": self._build_summary(order),
        }

    def get_summary(self) -> dict[str, Any]:
        order = self._get_order()
        if order is None:
            return {"ok": True, "message": "Order is empty.", "order": None}
        return {"ok": True, "message": "Order summary.", "order": self._build_summary(order)}

    def checkout(self) -> dict[str, Any]:
        order = self._get_order()
        if order is None:
            return {"ok": False, "message": "Order is empty."}
        if order.status != "draft":
            return {"ok": False, "message": "Order is not editable."}

        order.status = "submitted"
        order_service.recalc_totals(self._context.db, order=order)
        self._context.db.flush()

        return {"ok": True, "message": "Order submitted.", "order": self._build_summary(order)}
