from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, JSON, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    alias_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price_small: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    price_medium: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    price_large: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ingredient: Mapped[str | None] = mapped_column(String(512), nullable=True)
    note: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    availability: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    modifiers: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)

    variants: Mapped[list["MenuItemVariant"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "MenuItemVariant",
        back_populates="menu_item",
        cascade="all, delete-orphan",
        order_by="MenuItemVariant.sort_order",
    )

    def price_for_size(self, size: str | None) -> Decimal:
        """Return the price for a given size, falling back to base price."""
        if size == "small" and self.price_small is not None:
            return self.price_small
        if size == "medium" and self.price_medium is not None:
            return self.price_medium
        if size == "large" and self.price_large is not None:
            return self.price_large
        return self.price
