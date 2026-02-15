from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
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
    prefix="/store/menus",
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
        menu_id=item.menu_id,
        name=item.name,
        price=item.price,
        description=item.description,
        tags=item.tags,
        availability=item.availability,
        modifiers=item.modifiers,
    )


@router.get("", response_model=list[MenuOut])
def list_menus(
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> list[MenuOut]:
    menus = menu_service.list_menus(db, store_id=current_store.id)
    return [_menu_out(menu) for menu in menus]


@router.post("", response_model=MenuOut)
def create_menu(
    payload: MenuCreate,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> MenuOut:
    menu = menu_service.create_menu(db, store_id=current_store.id, payload=payload)
    db.commit()
    db.refresh(menu)
    return _menu_out(menu)


@router.get("/{menu_id}", response_model=MenuOut)
def get_menu(
    menu_id: uuid.UUID,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> MenuOut:
    menu = menu_service.get_menu(db, store_id=current_store.id, menu_id=menu_id)
    if menu is None:
        raise AppError(status_code=404, code="menu_not_found", detail="Menu not found")
    return _menu_out(menu)


@router.patch("/{menu_id}", response_model=MenuOut)
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


@router.delete("/{menu_id}")
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


@router.get("/{menu_id}/items", response_model=list[MenuItemOut])
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


@router.post("/{menu_id}/items", response_model=MenuItemOut)
def create_menu_item(
    menu_id: uuid.UUID,
    payload: MenuItemCreate,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> MenuItemOut:
    menu = menu_service.get_menu(db, store_id=current_store.id, menu_id=menu_id)
    if menu is None:
        raise AppError(status_code=404, code="menu_not_found", detail="Menu not found")

    item = menu_service.create_menu_item(db, menu_id=menu.id, payload=payload)
    db.commit()
    db.refresh(item)
    return _menu_item_out(item)


@router.patch("/{menu_id}/items/{item_id}", response_model=MenuItemOut)
def update_menu_item(
    menu_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: MenuItemUpdate,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> MenuItemOut:
    menu = menu_service.get_menu(db, store_id=current_store.id, menu_id=menu_id)
    if menu is None:
        raise AppError(status_code=404, code="menu_not_found", detail="Menu not found")

    item = menu_service.get_menu_item(db, menu_id=menu.id, item_id=item_id)
    if item is None:
        raise AppError(status_code=404, code="menu_item_not_found", detail="Menu item not found")

    menu_service.update_menu_item(db, item=item, payload=payload)
    db.commit()
    db.refresh(item)
    return _menu_item_out(item)


@router.delete("/{menu_id}/items/{item_id}")
def delete_menu_item(
    menu_id: uuid.UUID,
    item_id: uuid.UUID,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> dict:
    menu = menu_service.get_menu(db, store_id=current_store.id, menu_id=menu_id)
    if menu is None:
        raise AppError(status_code=404, code="menu_not_found", detail="Menu not found")

    item = menu_service.get_menu_item(db, menu_id=menu.id, item_id=item_id)
    if item is None:
        raise AppError(status_code=404, code="menu_item_not_found", detail="Menu item not found")

    menu_service.delete_menu_item(db, item=item)
    db.commit()
    return {"status": "ok"}
