from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow_naive
from app.db.base import Base


class OrderEvent(Base):
    """One change to a placed order (who, what, and how the total moved)."""

    __tablename__ = "order_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    # "store" for staff edits in the store portal.
    actor: Mapped[str] = mapped_column(String(16), nullable=False)
    # item_added | item_updated | item_removed | status_changed
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    # Human-readable summary, e.g. "2 × Beijing Beef (Large)" or "confirmed → cancelled".
    detail: Mapped[str] = mapped_column(String(512), nullable=False)
    total_before: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    total_after: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow_naive)
