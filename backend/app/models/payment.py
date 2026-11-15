from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow_naive
from app.db.base import Base


class Payment(Base):
    """One money movement on an order: a charge (customer pays) or a refund.

    The order's payment_status is derived from these rows (order_payments.sync_payment_status).
    """

    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    # charge | refund
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    # card (Stripe) | in_store (cash or card at the counter, recorded by staff) | dispute (chargeback lost)
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    # Always positive, in dollars.
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # pending | succeeded | failed | canceled
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    # Stripe PaymentIntent (pi_), Refund (re_) or Dispute (du_/dp_) id.
    stripe_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    # Card refunds: the charge they refund.
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow_naive, onupdate=utcnow_naive)
