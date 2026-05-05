from __future__ import annotations

import base64
import csv
import io
import json
import logging
import os
import uuid
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from google import genai

logger = logging.getLogger(__name__)

from app.api.deps.store import get_current_store_web
from app.api.host_policy import require_host_policy
from app.core.errors import AppError
from app.core.gemini_client import make_genai_client
from app.db.session import get_db
from app.models.menu import Menu
from app.models.menu_item import MenuItem
from app.models.menu_item_variant import MenuItemVariant
from app.models.store import Store
from app.schemas.common import Audience, PrincipalType
from app.schemas.menu.menu import (
    MenuCreate,
    MenuItemCreate,
    MenuItemOut,
    MenuItemUpdate,
    MenuItemVariantCreate,
    MenuItemVariantOut,
    MenuItemVariantUpdate,
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


def _variant_out(v: "MenuItemVariant") -> MenuItemVariantOut:  # type: ignore[name-defined]  # noqa: F821
    return MenuItemVariantOut(
        id=v.id,
        menu_item_id=v.menu_item_id,
        name=v.name,
        price=v.price,
        availability=v.availability,
        sort_order=v.sort_order,
        is_default=v.is_default,
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
        variants=[_variant_out(v) for v in (item.variants or [])],
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


@router.post("/items/upload-image")
async def upload_items_image(
    files: list[UploadFile] = File(...),
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> dict:
    """Upload menu screenshots/images/PDFs and use Gemini to extract menu items.

    Accepts multiple JPEG, PNG, WebP, or PDF files. Returns created/updated item counts.
    """
    allowed_types = {
        "image/jpeg", "image/png", "image/webp", "image/jpg",
        "application/pdf",
    }

    try:
        bundle = make_genai_client()
    except RuntimeError as exc:
        raise AppError(status_code=503, code="genai_unavailable", detail=str(exc))

    # Read and validate all files
    file_parts: list[genai.types.Part] = []
    for f in files:
        content_type = f.content_type or "image/jpeg"
        if content_type not in allowed_types:
            raise AppError(
                status_code=400,
                code="invalid_file",
                detail=f"File must be JPEG, PNG, WebP, or PDF (got {content_type} for {f.filename})",
            )
        file_bytes = await f.read()
        logger.info("Menu file upload: %s, %d bytes, type=%s", f.filename, len(file_bytes), content_type)
        if len(file_bytes) > 20 * 1024 * 1024:
            raise AppError(status_code=400, code="file_too_large", detail=f"File {f.filename} must be under 20MB")

        # Normalize MIME type
        mime_type = "image/jpeg" if content_type == "image/jpg" else content_type
        file_parts.append(genai.types.Part.from_bytes(data=file_bytes, mime_type=mime_type))

    prompt = """Analyze the restaurant menu image(s)/document(s) and extract all menu items.
Return a JSON array where each element has these fields:
- "name": string (required) — the item name
- "category": string or null — category/section (e.g. "Appetizers", "Entrees", "Drinks")
- "price": number or null — the base/default price
- "price_small": number or null — small size price if listed
- "price_medium": number or null — medium size price if listed
- "price_large": number or null — large size price if listed
- "description": string or null — item description if visible

Rules:
- Extract ALL items visible across all images/pages
- Deduplicate items that appear in multiple images
- If a price has a size indicator (S/M/L, Small/Medium/Large, Pt/Qt), use the size-specific fields
- If only one price is shown, put it in "price"
- Use null for missing fields, not empty strings
- Return ONLY the JSON array, no markdown formatting, no explanation"""

    try:
        response = bundle.client.models.generate_content(
            model=bundle.background_model,
            contents=[*file_parts, prompt],
        )

        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3].strip()
        if text.startswith("json"):
            text = text[4:].strip()

        items_data = json.loads(text)
        if not isinstance(items_data, list):
            raise AppError(status_code=500, code="parse_error", detail="Gemini did not return a JSON array")

    except json.JSONDecodeError:
        raw = response.text[:500] if response and response.text else "(empty)"
        logger.error("Gemini returned non-JSON: %s", raw)
        raise AppError(status_code=500, code="parse_error", detail=f"Failed to parse Gemini response as JSON: {raw[:200]}")
    except Exception as e:
        if isinstance(e, AppError):
            raise
        logger.error("Gemini API error: %s", e, exc_info=True)
        raise AppError(status_code=500, code="gemini_error", detail=f"Gemini API error: {e}")

    # Match existing items by name to avoid duplicates
    existing = menu_service.list_store_items(db, store_id=current_store.id)
    by_name: dict[str, MenuItem] = {item.name.lower(): item for item in existing}

    created = 0
    updated = 0
    errors: list[str] = []

    for i, item_data in enumerate(items_data):
        if not isinstance(item_data, dict):
            errors.append(f"Item {i + 1}: not a valid object, skipped")
            continue

        name = (item_data.get("name") or "").strip()
        if not name:
            errors.append(f"Item {i + 1}: missing name, skipped")
            continue

        def _to_decimal(val: object) -> Decimal | None:
            if val is None:
                return None
            try:
                return Decimal(str(val))
            except (InvalidOperation, ValueError):
                return None

        price = _to_decimal(item_data.get("price"))
        price_small = _to_decimal(item_data.get("price_small"))
        price_medium = _to_decimal(item_data.get("price_medium"))
        price_large = _to_decimal(item_data.get("price_large"))

        # Resolve a base price from available prices
        base_price = price or price_medium or price_small or price_large
        if base_price is None:
            errors.append(f"Item {i + 1} '{name}': no price found, skipped")
            continue

        category = (item_data.get("category") or "").strip() or None
        description = (item_data.get("description") or "").strip() or None

        existing_item = by_name.get(name.lower())
        if existing_item:
            existing_item.price = base_price
            if price_small is not None:
                existing_item.price_small = price_small
            if price_medium is not None:
                existing_item.price_medium = price_medium
            if price_large is not None:
                existing_item.price_large = price_large
            if category:
                existing_item.category = category
            if description:
                existing_item.description = description
            updated += 1
        else:
            new_item = MenuItem(
                store_id=current_store.id,
                name=name,
                price=base_price,
                price_small=price_small,
                price_medium=price_medium,
                price_large=price_large,
                category=category,
                description=description,
            )
            db.add(new_item)
            by_name[name.lower()] = new_item
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


# ── Item variants (Coke: 12 Oz Can / 2 Liter, Pizza: 10" / 14" / 18") ──

@router.get("/items/{item_id}/variants", response_model=list[MenuItemVariantOut])
def list_item_variants_endpoint(
    item_id: uuid.UUID,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> list[MenuItemVariantOut]:
    item = menu_service.get_store_item(db, store_id=current_store.id, item_id=item_id)
    if item is None:
        raise AppError(status_code=404, code="item_not_found", detail="Item not found")
    rows = menu_service.list_item_variants(db, menu_item_id=item_id)
    return [_variant_out(v) for v in rows]


@router.post("/items/{item_id}/variants", response_model=MenuItemVariantOut)
def create_item_variant_endpoint(
    item_id: uuid.UUID,
    payload: MenuItemVariantCreate,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> MenuItemVariantOut:
    item = menu_service.get_store_item(db, store_id=current_store.id, item_id=item_id)
    if item is None:
        raise AppError(status_code=404, code="item_not_found", detail="Item not found")

    existing = menu_service.find_variant_by_name(
        db, menu_item_id=item_id, name=payload.name
    )
    if existing is not None:
        raise AppError(
            status_code=409,
            code="variant_name_exists",
            detail=f"A variant named '{payload.name}' already exists on this item.",
        )

    variant = menu_service.create_item_variant(db, menu_item_id=item_id, payload=payload)
    db.commit()
    db.refresh(variant)
    return _variant_out(variant)


@router.patch("/items/{item_id}/variants/{variant_id}", response_model=MenuItemVariantOut)
def update_item_variant_endpoint(
    item_id: uuid.UUID,
    variant_id: uuid.UUID,
    payload: MenuItemVariantUpdate,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> MenuItemVariantOut:
    item = menu_service.get_store_item(db, store_id=current_store.id, item_id=item_id)
    if item is None:
        raise AppError(status_code=404, code="item_not_found", detail="Item not found")
    variant = menu_service.get_item_variant(db, menu_item_id=item_id, variant_id=variant_id)
    if variant is None:
        raise AppError(status_code=404, code="variant_not_found", detail="Variant not found")

    # Rename collision check.
    if payload.name is not None:
        conflicting = menu_service.find_variant_by_name(
            db, menu_item_id=item_id, name=payload.name
        )
        if conflicting is not None and conflicting.id != variant.id:
            raise AppError(
                status_code=409,
                code="variant_name_exists",
                detail=f"A variant named '{payload.name}' already exists on this item.",
            )

    menu_service.update_item_variant(db, variant=variant, payload=payload)
    db.commit()
    db.refresh(variant)
    return _variant_out(variant)


@router.delete("/items/{item_id}/variants/{variant_id}")
def delete_item_variant_endpoint(
    item_id: uuid.UUID,
    variant_id: uuid.UUID,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> dict:
    item = menu_service.get_store_item(db, store_id=current_store.id, item_id=item_id)
    if item is None:
        raise AppError(status_code=404, code="item_not_found", detail="Item not found")
    variant = menu_service.get_item_variant(db, menu_item_id=item_id, variant_id=variant_id)
    if variant is None:
        raise AppError(status_code=404, code="variant_not_found", detail="Variant not found")

    menu_service.delete_item_variant(db, variant=variant)
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
