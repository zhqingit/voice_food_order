from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.menu import Menu
from app.models.menu_item import MenuItem
from app.schemas.menu.menu import MenuCreate, MenuItemCreate, MenuItemUpdate, MenuUpdate


def list_menus(db: Session, *, store_id: uuid.UUID) -> list[Menu]:
    return db.execute(select(Menu).where(Menu.store_id == store_id).order_by(Menu.updated_at.desc())).scalars().all()


def get_menu(db: Session, *, store_id: uuid.UUID, menu_id: uuid.UUID) -> Menu | None:
    return db.execute(select(Menu).where(Menu.store_id == store_id, Menu.id == menu_id)).scalar_one_or_none()


def get_menu_by_version(db: Session, *, store_id: uuid.UUID, version: int | None) -> Menu | None:
    query = select(Menu).where(Menu.store_id == store_id)
    if version is not None:
        query = query.where(Menu.version == version)
        return db.execute(query).scalar_one_or_none()

    query = query.where(Menu.active.is_(True)).order_by(Menu.updated_at.desc())
    return db.execute(query).scalar_one_or_none()


def create_menu(db: Session, *, store_id: uuid.UUID, payload: MenuCreate) -> Menu:
    max_version = db.execute(select(func.max(Menu.version)).where(Menu.store_id == store_id)).scalar_one()
    next_version = (max_version or 0) + 1

    menu = Menu(
        store_id=store_id,
        name=payload.name,
        active=payload.active,
        version=next_version,
    )
    db.add(menu)
    return menu


def update_menu(db: Session, *, menu: Menu, payload: MenuUpdate) -> Menu:
    touched = False
    if payload.name is not None and payload.name != menu.name:
        menu.name = payload.name
        touched = True
    if payload.active is not None and payload.active != menu.active:
        menu.active = payload.active
        touched = True

    if touched:
        menu.version += 1
    return menu


def delete_menu(db: Session, *, menu: Menu) -> None:
    db.delete(menu)


def list_menu_items(db: Session, *, menu_id: uuid.UUID) -> list[MenuItem]:
    return db.execute(select(MenuItem).where(MenuItem.menu_id == menu_id).order_by(MenuItem.name.asc())).scalars().all()


def get_menu_item(db: Session, *, menu_id: uuid.UUID, item_id: uuid.UUID) -> MenuItem | None:
    return db.execute(select(MenuItem).where(MenuItem.menu_id == menu_id, MenuItem.id == item_id)).scalar_one_or_none()


def create_menu_item(db: Session, *, menu_id: uuid.UUID, payload: MenuItemCreate) -> MenuItem:
    item = MenuItem(
        menu_id=menu_id,
        name=payload.name,
        price=payload.price,
        description=payload.description,
        tags=payload.tags,
        availability=payload.availability,
        modifiers=payload.modifiers,
    )
    db.add(item)
    return item


def update_menu_item(db: Session, *, item: MenuItem, payload: MenuItemUpdate) -> MenuItem:
    if payload.name is not None:
        item.name = payload.name
    if payload.price is not None:
        item.price = payload.price
    if payload.description is not None:
        item.description = payload.description
    if payload.tags is not None:
        item.tags = payload.tags
    if payload.availability is not None:
        item.availability = payload.availability
    if payload.modifiers is not None:
        item.modifiers = payload.modifiers
    return item


def delete_menu_item(db: Session, *, item: MenuItem) -> None:
    db.delete(item)
