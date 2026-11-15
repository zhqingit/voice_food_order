from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow_naive
from app.db.base import Base


class PhoneCall(Base):
    """One call answered by the AI on a store's phone line, with what it cost us."""

    __tablename__ = "phone_calls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    call_sid: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    caller: Mapped[str | None] = mapped_column(String(32), nullable=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    # hangup | transfer | max_duration | error
    end_reason: Mapped[str] = mapped_column(String(32), nullable=False)
    # Time the AI was on the line (the media stream).
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ai_cost: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False, default=Decimal("0"))
    # Estimated: billed minutes × settings.phone_cost_per_minute.
    telephony_cost: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow_naive, index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
