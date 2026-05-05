from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow_naive
from app.db.base import Base


class MenuItemVariant(Base):
    """A named, priced option on a MenuItem.

    Examples: ``Coke`` has two variants — "12 Oz Can" ($2.99) and "2 Liter"
    ($4.99). Each variant has its own availability flag so the store can mark
    "2 Liter out of stock" without affecting the 12 Oz Can.

    An item with zero variants is a simple single-price item; its
    ``menu_items.price`` is used. An item with one or more variants requires
    the customer to pick one before ordering.
    """

    __tablename__ = "menu_item_variants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    menu_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("menu_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(64), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    availability: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Lower number first when the bot reads out variants to the customer.
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Selected when the customer orders the item without specifying a variant.
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow_naive)

    menu_item: Mapped["MenuItem"] = relationship("MenuItem", back_populates="variants")  # type: ignore[name-defined]  # noqa: F821
