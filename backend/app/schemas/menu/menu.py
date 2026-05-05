from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel, Field


class MenuOut(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    name: str
    active: bool
    version: int
    updated_at: datetime


class MenuCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    active: bool = True


class MenuUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    active: bool | None = None


class MenuItemVariantOut(BaseModel):
    id: uuid.UUID
    menu_item_id: uuid.UUID
    name: str
    price: Decimal
    availability: bool = True
    sort_order: int = 0
    is_default: bool = False


class MenuItemVariantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    price: Decimal = Field(ge=0)
    availability: bool = True
    sort_order: int = 0
    is_default: bool = False


class MenuItemVariantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    price: Decimal | None = Field(default=None, ge=0)
    availability: bool | None = None
    sort_order: int | None = None
    is_default: bool | None = None


class MenuItemOut(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    name: str
    alias_name: str | None = None
    category: str | None = None
    price: Decimal
    price_small: Decimal | None = None
    price_medium: Decimal | None = None
    price_large: Decimal | None = None
    description: str | None = None
    ingredient: str | None = None
    note: str | None = None
    tags: list[str] | None = None
    availability: bool
    modifiers: dict[str, object] | None = None
    variants: list[MenuItemVariantOut] = []


class MenuItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    alias_name: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=255)
    price: Decimal
    price_small: Decimal | None = None
    price_medium: Decimal | None = None
    price_large: Decimal | None = None
    description: str | None = Field(default=None, max_length=512)
    ingredient: str | None = Field(default=None, max_length=512)
    note: str | None = Field(default=None, max_length=512)
    tags: list[str] | None = None
    availability: bool = True
    modifiers: dict[str, object] | None = None


class MenuItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    alias_name: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=255)
    price: Decimal | None = None
    price_small: Decimal | None = None
    price_medium: Decimal | None = None
    price_large: Decimal | None = None
    description: str | None = Field(default=None, max_length=512)
    ingredient: str | None = Field(default=None, max_length=512)
    note: str | None = Field(default=None, max_length=512)
    tags: list[str] | None = None
    availability: bool | None = None
    modifiers: dict[str, object] | None = None
