from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.menu import Menu
from app.models.menu_item import MenuItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.schemas.order.order import OrderCreate


def get_menu_item_for_store(db: Session, *, store_id: uuid.UUID, item_id: uuid.UUID) -> MenuItem | None:
    return db.execute(
        select(MenuItem)
        .join(Menu, Menu.id == MenuItem.menu_id)
        .where(Menu.store_id == store_id)
        .where(MenuItem.id == item_id)
    ).scalar_one_or_none()


def create_draft_order(db: Session, *, payload: OrderCreate) -> Order:
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


def create_order_item(db: Session, *, order: Order, menu_item: MenuItem, quantity: int) -> OrderItem:
    item = OrderItem(
        order_id=order.id,
        menu_item_id=menu_item.id,
        quantity=quantity,
        price_snapshot=menu_item.price,
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


def recalc_totals(db: Session, *, order: Order) -> Order:
    items = db.execute(select(OrderItem).where(OrderItem.order_id == order.id)).scalars().all()
    subtotal = sum((item.price_snapshot * item.quantity for item in items), Decimal("0.00"))
    tax = Decimal("0.00")
    total = subtotal + tax

    order.subtotal = subtotal
    order.tax = tax
    order.total = total
    return order
