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


class MenuItemOut(BaseModel):
    id: uuid.UUID
    menu_id: uuid.UUID
    name: str
    price: Decimal
    description: str | None = None
    tags: list[str] | None = None
    availability: bool
    modifiers: dict[str, object] | None = None


class MenuItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    price: Decimal
    description: str | None = Field(default=None, max_length=512)
    tags: list[str] | None = None
    availability: bool = True
    modifiers: dict[str, object] | None = None


class MenuItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    price: Decimal | None = None
    description: str | None = Field(default=None, max_length=512)
    tags: list[str] | None = None
    availability: bool | None = None
    modifiers: dict[str, object] | None = None
