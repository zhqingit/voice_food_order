from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow_naive
from app.db.base import Base


class Promotion(Base):
    """A discount a store funds itself, applied automatically to qualifying orders.

    The terms (kind, value, minimum, channels) can't change once created: an
    order keeps the promotion it was placed with, so changing the terms would
    change past orders. A store ends a promotion and creates a new one instead.
    """

    __tablename__ = "promotions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # percent: `value` percent off the subtotal; amount_off: `value` dollars off.
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # Pre-tax subtotal the order must reach (0 = any order).
    min_subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    # all | app | phone
    channels: Mapped[str] = mapped_column(String(8), nullable=False, default="all")
    # Store-local dates, inclusive; None = open-ended.
    starts_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow_naive, onupdate=utcnow_naive)
