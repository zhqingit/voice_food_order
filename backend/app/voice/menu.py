"""Load the active menu for a store and format it as lines for the system prompt."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.services.menu_service import get_menu_by_version, list_menu_items


def load_menu_for_store(db: Session, store_id: uuid.UUID) -> list[str]:
    """Return the active menu for *store_id* as human-readable lines.

    Each line describes one menu item with its name, alias, price(s),
    ingredients, and notes so the LLM can reference it in conversation.
    Returns an empty list if no active menu exists.
    """
    menu = get_menu_by_version(db, store_id=store_id, version=None)
    if menu is None:
        return []

    items = [i for i in list_menu_items(db, menu_id=menu.id) if i.availability]
    if not items:
        return []

    lines: list[str] = [f"Restaurant Menu: {menu.name}", ""]
    for item in items:
        parts = [f"- {item.name}"]
        if item.alias_name:
            parts.append(f"({item.alias_name})")

        # Show size prices if available, otherwise base price
        has_sizes = item.price_small is not None or item.price_medium is not None or item.price_large is not None
        if has_sizes:
            size_parts = []
            if item.price_small is not None:
                size_parts.append(f"S ${item.price_small}")
            if item.price_medium is not None:
                size_parts.append(f"M ${item.price_medium}")
            if item.price_large is not None:
                size_parts.append(f"L ${item.price_large}")
            parts.append(f"— {' / '.join(size_parts)}")
        else:
            parts.append(f"— ${item.price}")

        line = " ".join(parts)

        details: list[str] = []
        if item.category:
            details.append(f"Category: {item.category}")
        if item.ingredient:
            details.append(f"Ingredients: {item.ingredient}")
        if item.note:
            details.append(f"Note: {item.note}")
        if item.tags:
            details.append(f"Tags: {', '.join(item.tags)}")

        if details:
            line += "\n    " + " | ".join(details)

        lines.append(line)

    return lines
