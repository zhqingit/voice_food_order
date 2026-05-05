from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.menu import Menu
from app.models.menu_item import MenuItem
from app.models.menu_item_variant import MenuItemVariant
from app.models.menu_menu_item import MenuMenuItem
from app.schemas.menu.menu import (
    MenuCreate,
    MenuItemCreate,
    MenuItemUpdate,
    MenuItemVariantCreate,
    MenuItemVariantUpdate,
    MenuUpdate,
)


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
    # ``model_dump(exclude_unset=True)`` returns only fields the client
    # explicitly sent, so a null value for a nullable field clears it (previous
    # ``is not None`` checks silently ignored those). Required NOT-NULL fields
    # (``name``, ``price``, ``availability``) are skipped if the client sent
    # null, so a malformed request can't blank them out.
    non_nullable = {"name", "price", "availability"}
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if value is None and key in non_nullable:
            continue
        setattr(item, key, value)
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


# ── Menu item variants ────────────────────────────────────────

def list_item_variants(db: Session, *, menu_item_id: uuid.UUID) -> list[MenuItemVariant]:
    return db.execute(
        select(MenuItemVariant)
        .where(MenuItemVariant.menu_item_id == menu_item_id)
        .order_by(MenuItemVariant.sort_order.asc(), MenuItemVariant.name.asc())
    ).scalars().all()


def get_item_variant(
    db: Session, *, menu_item_id: uuid.UUID, variant_id: uuid.UUID
) -> MenuItemVariant | None:
    return db.execute(
        select(MenuItemVariant).where(
            MenuItemVariant.menu_item_id == menu_item_id,
            MenuItemVariant.id == variant_id,
        )
    ).scalar_one_or_none()


def find_variant_by_name(
    db: Session, *, menu_item_id: uuid.UUID, name: str
) -> MenuItemVariant | None:
    """Case-insensitive exact match, then containment fallback — mirrors the
    fuzzy style we already use for item lookup so the bot can say '2 liter'
    and hit the '2 Liter' variant row."""
    n = (name or "").strip().lower()
    if not n:
        return None
    rows = list_item_variants(db, menu_item_id=menu_item_id)
    for v in rows:
        if v.name.lower() == n:
            return v
    for v in rows:
        if n in v.name.lower() or v.name.lower() in n:
            return v
    return None


def create_item_variant(
    db: Session, *, menu_item_id: uuid.UUID, payload: MenuItemVariantCreate
) -> MenuItemVariant:
    # If marking this one as default, clear any existing default.
    if payload.is_default:
        for v in list_item_variants(db, menu_item_id=menu_item_id):
            if v.is_default:
                v.is_default = False
    variant = MenuItemVariant(
        menu_item_id=menu_item_id,
        name=payload.name.strip(),
        price=payload.price,
        availability=payload.availability,
        sort_order=payload.sort_order,
        is_default=payload.is_default,
    )
    db.add(variant)
    return variant


def update_item_variant(
    db: Session, *, variant: MenuItemVariant, payload: MenuItemVariantUpdate
) -> MenuItemVariant:
    if payload.name is not None:
        variant.name = payload.name.strip()
    if payload.price is not None:
        variant.price = payload.price
    if payload.availability is not None:
        variant.availability = payload.availability
    if payload.sort_order is not None:
        variant.sort_order = payload.sort_order
    if payload.is_default is not None and payload.is_default and not variant.is_default:
        # Promoting to default: demote any existing default on the same item.
        for v in list_item_variants(db, menu_item_id=variant.menu_item_id):
            if v.id != variant.id and v.is_default:
                v.is_default = False
        variant.is_default = True
    elif payload.is_default is False:
        variant.is_default = False
    return variant


def delete_item_variant(db: Session, *, variant: MenuItemVariant) -> None:
    db.delete(variant)
