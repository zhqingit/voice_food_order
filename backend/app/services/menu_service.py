from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.menu import Menu
from app.models.menu_item import MenuItem
from app.models.menu_menu_item import MenuMenuItem
from app.schemas.menu.menu import MenuCreate, MenuItemCreate, MenuItemUpdate, MenuUpdate


# ── Menus ──────────────────────────────────────────────────────

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


def set_default_menu(db: Session, *, store_id: uuid.UUID, menu: Menu) -> Menu:
    for m in db.execute(select(Menu).where(Menu.store_id == store_id, Menu.active.is_(True))).scalars().all():
        if m.id != menu.id:
            m.active = False
    menu.active = True
    return menu


def delete_menu(db: Session, *, menu: Menu) -> None:
    db.delete(menu)


# ── Store Items (pool) ─────────────────────────────────────────

def list_store_items(db: Session, *, store_id: uuid.UUID) -> list[MenuItem]:
    return db.execute(select(MenuItem).where(MenuItem.store_id == store_id).order_by(MenuItem.name.asc())).scalars().all()


def get_store_item(db: Session, *, store_id: uuid.UUID, item_id: uuid.UUID) -> MenuItem | None:
    return db.execute(select(MenuItem).where(MenuItem.store_id == store_id, MenuItem.id == item_id)).scalar_one_or_none()


def create_store_item(db: Session, *, store_id: uuid.UUID, payload: MenuItemCreate) -> MenuItem:
    item = MenuItem(
        store_id=store_id,
        name=payload.name,
        alias_name=payload.alias_name,
        category=payload.category,
        price=payload.price,
        price_small=payload.price_small,
        price_medium=payload.price_medium,
        price_large=payload.price_large,
        description=payload.description,
        ingredient=payload.ingredient,
        note=payload.note,
        tags=payload.tags,
        availability=payload.availability,
        modifiers=payload.modifiers,
    )
    db.add(item)
    return item


def update_store_item(db: Session, *, item: MenuItem, payload: MenuItemUpdate) -> MenuItem:
    if payload.name is not None:
        item.name = payload.name
    if payload.alias_name is not None:
        item.alias_name = payload.alias_name
    if payload.category is not None:
        item.category = payload.category
    if payload.price is not None:
        item.price = payload.price
    if payload.price_small is not None:
        item.price_small = payload.price_small
    if payload.price_medium is not None:
        item.price_medium = payload.price_medium
    if payload.price_large is not None:
        item.price_large = payload.price_large
    if payload.description is not None:
        item.description = payload.description
    if payload.ingredient is not None:
        item.ingredient = payload.ingredient
    if payload.note is not None:
        item.note = payload.note
    if payload.tags is not None:
        item.tags = payload.tags
    if payload.availability is not None:
        item.availability = payload.availability
    if payload.modifiers is not None:
        item.modifiers = payload.modifiers
    return item


def delete_store_item(db: Session, *, item: MenuItem) -> None:
    db.delete(item)


# ── Menu ↔ Item links (junction) ──────────────────────────────

def list_menu_items(db: Session, *, menu_id: uuid.UUID) -> list[MenuItem]:
    return db.execute(
        select(MenuItem)
        .join(MenuMenuItem, MenuMenuItem.menu_item_id == MenuItem.id)
        .where(MenuMenuItem.menu_id == menu_id)
        .order_by(MenuItem.name.asc())
    ).scalars().all()


def add_item_to_menu(db: Session, *, menu_id: uuid.UUID, item_id: uuid.UUID) -> MenuMenuItem:
    link = MenuMenuItem(menu_id=menu_id, menu_item_id=item_id)
    db.add(link)
    return link


def remove_item_from_menu(db: Session, *, menu_id: uuid.UUID, item_id: uuid.UUID) -> bool:
    link = db.execute(
        select(MenuMenuItem).where(MenuMenuItem.menu_id == menu_id, MenuMenuItem.menu_item_id == item_id)
    ).scalar_one_or_none()
    if link is None:
        return False
    db.delete(link)
    return True


def get_menu_item_ids(db: Session, *, menu_id: uuid.UUID) -> set[uuid.UUID]:
    rows = db.execute(select(MenuMenuItem.menu_item_id).where(MenuMenuItem.menu_id == menu_id)).scalars().all()
    return set(rows)
