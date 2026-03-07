from __future__ import annotations

import csv
import io
import uuid
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.api.deps.store import get_current_store_web
from app.api.host_policy import require_host_policy
from app.core.errors import AppError
from app.db.session import get_db
from app.models.menu import Menu
from app.models.menu_item import MenuItem
from app.models.store import Store
from app.schemas.common import Audience, PrincipalType
from app.schemas.menu.menu import (
    MenuCreate,
    MenuItemCreate,
    MenuItemOut,
    MenuItemUpdate,
    MenuOut,
    MenuUpdate,
)
from app.services import menu_service

router = APIRouter(
    prefix="/store",
    tags=["store-menu"],
    dependencies=[Depends(require_host_policy(principal=PrincipalType.store, audience=Audience.web))],
)


def _menu_out(menu: Menu) -> MenuOut:
    return MenuOut(
        id=menu.id,
        store_id=menu.store_id,
        name=menu.name,
        active=menu.active,
        version=menu.version,
        updated_at=menu.updated_at,
    )


def _menu_item_out(item: MenuItem) -> MenuItemOut:
    return MenuItemOut(
        id=item.id,
        store_id=item.store_id,
        name=item.name,
        alias_name=item.alias_name,
        category=item.category,
        price=item.price,
        price_small=item.price_small,
        price_medium=item.price_medium,
        price_large=item.price_large,
        description=item.description,
        ingredient=item.ingredient,
        note=item.note,
        tags=item.tags,
        availability=item.availability,
        modifiers=item.modifiers,
    )


# ── Menus ──────────────────────────────────────────────────────

@router.get("/menus", response_model=list[MenuOut])
def list_menus(
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> list[MenuOut]:
    menus = menu_service.list_menus(db, store_id=current_store.id)
    return [_menu_out(menu) for menu in menus]


@router.post("/menus", response_model=MenuOut)
def create_menu(
    payload: MenuCreate,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> MenuOut:
    menu = menu_service.create_menu(db, store_id=current_store.id, payload=payload)
    db.commit()
    db.refresh(menu)
    return _menu_out(menu)


@router.get("/menus/{menu_id}", response_model=MenuOut)
def get_menu(
    menu_id: uuid.UUID,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> MenuOut:
    menu = menu_service.get_menu(db, store_id=current_store.id, menu_id=menu_id)
    if menu is None:
        raise AppError(status_code=404, code="menu_not_found", detail="Menu not found")
    return _menu_out(menu)


@router.patch("/menus/{menu_id}", response_model=MenuOut)
def update_menu(
    menu_id: uuid.UUID,
    payload: MenuUpdate,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> MenuOut:
    menu = menu_service.get_menu(db, store_id=current_store.id, menu_id=menu_id)
    if menu is None:
        raise AppError(status_code=404, code="menu_not_found", detail="Menu not found")

    menu_service.update_menu(db, menu=menu, payload=payload)
    db.commit()
    db.refresh(menu)
    return _menu_out(menu)


@router.post("/menus/{menu_id}/set-default")
def set_default_menu(
    menu_id: uuid.UUID,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> MenuOut:
    menu = menu_service.get_menu(db, store_id=current_store.id, menu_id=menu_id)
    if menu is None:
        raise AppError(status_code=404, code="menu_not_found", detail="Menu not found")

    menu_service.set_default_menu(db, store_id=current_store.id, menu=menu)
    db.commit()
    db.refresh(menu)
    return _menu_out(menu)


@router.delete("/menus/{menu_id}")
def delete_menu(
    menu_id: uuid.UUID,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> dict:
    menu = menu_service.get_menu(db, store_id=current_store.id, menu_id=menu_id)
    if menu is None:
        raise AppError(status_code=404, code="menu_not_found", detail="Menu not found")

    menu_service.delete_menu(db, menu=menu)
    db.commit()
    return {"status": "ok"}


# ── Store Items (pool) ─────────────────────────────────────────

@router.get("/items", response_model=list[MenuItemOut])
def list_store_items(
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> list[MenuItemOut]:
    items = menu_service.list_store_items(db, store_id=current_store.id)
    return [_menu_item_out(item) for item in items]


@router.post("/items", response_model=MenuItemOut)
def create_store_item(
    payload: MenuItemCreate,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> MenuItemOut:
    item = menu_service.create_store_item(db, store_id=current_store.id, payload=payload)
    db.commit()
    db.refresh(item)
    return _menu_item_out(item)


@router.post("/items/upload-csv")
async def upload_items_csv(
    file: UploadFile = File(...),
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> dict:
    """Upload a CSV to create or update items in the store pool.

    CSV columns: name (required), alias_name, category, price (required),
    price_small, price_medium, price_large, description, ingredient, note,
    tags (comma-separated within quotes), availability (true/false).

    Items are matched by name (case-insensitive). Existing items are updated,
    new items are created.
    """
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise AppError(status_code=400, code="invalid_csv", detail="File must be UTF-8 encoded")

    # Normalize column names: lowercase, strip, underscores
    raw_reader = csv.DictReader(io.StringIO(text))
    if not raw_reader.fieldnames:
        raise AppError(status_code=400, code="invalid_csv", detail="CSV is empty or has no header")

    # Map original column names → normalized keys
    col_aliases: dict[str, str] = {
        "item_name": "name",
        "item name": "name",
        "alias_name": "alias_name",
        "alias name": "alias_name",
        "aliasname": "alias_name",
        "price_small": "price_small",
        "price small": "price_small",
        "small": "price_small",
        "price_medium": "price_medium",
        "price medium": "price_medium",
        "medium": "price_medium",
        "price_large": "price_large",
        "price large": "price_large",
        "large": "price_large",
    }

    def _normalize_col(col: str) -> str:
        key = col.strip().lower().replace(" ", "_")
        return col_aliases.get(key, key)

    col_map = {orig: _normalize_col(orig) for orig in raw_reader.fieldnames}

    # Re-read rows with normalized keys
    rows: list[dict[str, str]] = []
    for raw_row in raw_reader:
        rows.append({col_map[k]: v for k, v in raw_row.items()})

    # Verify we have a name column after normalization
    norm_cols = set(col_map.values())
    if "name" not in norm_cols:
        raise AppError(status_code=400, code="invalid_csv", detail="CSV must have a 'name' (or 'item_name') column")

    existing = menu_service.list_store_items(db, store_id=current_store.id)
    by_name: dict[str, MenuItem] = {item.name.lower(): item for item in existing}

    created = 0
    updated = 0
    errors: list[str] = []

    for row_num, row in enumerate(rows, start=2):
        name = (row.get("name") or "").strip()
        if not name:
            errors.append(f"Row {row_num}: missing name, skipped")
            continue

        def _parse_opt_decimal(key: str) -> Decimal | None:
            v = (row.get(key) or "").strip()
            if not v:
                return None
            try:
                return Decimal(v)
            except InvalidOperation:
                return None

        def _parse_opt_str(key: str) -> str | None:
            v = (row.get(key) or "").strip()
            return v if v else None

        # Resolve base price: explicit 'price' column, or fall back to price_medium
        price_dec = _parse_opt_decimal("price")
        if price_dec is None:
            price_dec = _parse_opt_decimal("price_medium")
        if price_dec is None:
            price_dec = _parse_opt_decimal("price_small")
        if price_dec is None:
            price_dec = _parse_opt_decimal("price_large")
        if price_dec is None:
            errors.append(f"Row {row_num}: no price found for '{name}', skipped")
            continue
        price = price_dec

        tags_raw = _parse_opt_str("tags")
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else None

        avail_str = (row.get("availability") or "").strip().lower()
        availability = avail_str not in ("false", "0", "no") if avail_str else True

        item = by_name.get(name.lower())
        if item:
            item.alias_name = _parse_opt_str("alias_name") or item.alias_name
            item.category = _parse_opt_str("category") or item.category
            item.price = price
            item.price_small = _parse_opt_decimal("price_small") or item.price_small
            item.price_medium = _parse_opt_decimal("price_medium") or item.price_medium
            item.price_large = _parse_opt_decimal("price_large") or item.price_large
            item.description = _parse_opt_str("description") or item.description
            item.ingredient = _parse_opt_str("ingredient") or item.ingredient
            item.note = _parse_opt_str("note") or item.note
            if tags is not None:
                item.tags = tags
            item.availability = availability
            updated += 1
        else:
            item = MenuItem(
                store_id=current_store.id,
                name=name,
                alias_name=_parse_opt_str("alias_name"),
                category=_parse_opt_str("category"),
                price=price,
                price_small=_parse_opt_decimal("price_small"),
                price_medium=_parse_opt_decimal("price_medium"),
                price_large=_parse_opt_decimal("price_large"),
                description=_parse_opt_str("description"),
                ingredient=_parse_opt_str("ingredient"),
                note=_parse_opt_str("note"),
                tags=tags,
                availability=availability,
            )
            db.add(item)
            by_name[name.lower()] = item
            created += 1

    db.commit()
    return {"created": created, "updated": updated, "errors": errors}


@router.patch("/items/{item_id}", response_model=MenuItemOut)
def update_store_item(
    item_id: uuid.UUID,
    payload: MenuItemUpdate,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> MenuItemOut:
    item = menu_service.get_store_item(db, store_id=current_store.id, item_id=item_id)
    if item is None:
        raise AppError(status_code=404, code="item_not_found", detail="Item not found")

    menu_service.update_store_item(db, item=item, payload=payload)
    db.commit()
    db.refresh(item)
    return _menu_item_out(item)


@router.delete("/items/{item_id}")
def delete_store_item(
    item_id: uuid.UUID,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> dict:
    item = menu_service.get_store_item(db, store_id=current_store.id, item_id=item_id)
    if item is None:
        raise AppError(status_code=404, code="item_not_found", detail="Item not found")

    menu_service.delete_store_item(db, item=item)
    db.commit()
    return {"status": "ok"}


# ── Menu ↔ Item links ─────────────────────────────────────────

@router.get("/menus/{menu_id}/items", response_model=list[MenuItemOut])
def list_menu_items(
    menu_id: uuid.UUID,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> list[MenuItemOut]:
    menu = menu_service.get_menu(db, store_id=current_store.id, menu_id=menu_id)
    if menu is None:
        raise AppError(status_code=404, code="menu_not_found", detail="Menu not found")

    items = menu_service.list_menu_items(db, menu_id=menu.id)
    return [_menu_item_out(item) for item in items]


@router.post("/menus/{menu_id}/items/{item_id}")
def add_item_to_menu(
    menu_id: uuid.UUID,
    item_id: uuid.UUID,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> dict:
    menu = menu_service.get_menu(db, store_id=current_store.id, menu_id=menu_id)
    if menu is None:
        raise AppError(status_code=404, code="menu_not_found", detail="Menu not found")

    item = menu_service.get_store_item(db, store_id=current_store.id, item_id=item_id)
    if item is None:
        raise AppError(status_code=404, code="item_not_found", detail="Item not found")

    menu_service.add_item_to_menu(db, menu_id=menu.id, item_id=item.id)
    db.commit()
    return {"status": "ok"}


@router.delete("/menus/{menu_id}/items/{item_id}")
def remove_item_from_menu(
    menu_id: uuid.UUID,
    item_id: uuid.UUID,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> dict:
    menu = menu_service.get_menu(db, store_id=current_store.id, menu_id=menu_id)
    if menu is None:
        raise AppError(status_code=404, code="menu_not_found", detail="Menu not found")

    removed = menu_service.remove_item_from_menu(db, menu_id=menu.id, item_id=item_id)
    if not removed:
        raise AppError(status_code=404, code="link_not_found", detail="Item not in this menu")

    db.commit()
    return {"status": "ok"}
