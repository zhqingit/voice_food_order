from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow_naive
from app.db.base import Base


class StoreInvoice(Base):
    """The platform's monthly bill to a store: commission on orders paid at the
    store (not taken through Stripe), the monthly fee, and admin adjustments.

    draft → (admin sends; Stripe Invoicing emails it) open → paid | uncollectible
    A draft can be deleted; a sent invoice can be voided. Either way its orders
    become billable again.
    """

    __tablename__ = "store_invoices"
    __table_args__ = (
        # One live invoice per store and month.
        Index(
            "uq_store_invoices_store_period_live",
            "store_id",
            "period",
            unique=True,
            postgresql_where=text("status <> 'void'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    # First day of the month billed.
    period: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # draft | open | paid | void | uncollectible
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))

    stripe_invoice_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    hosted_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Paid by check or cash, marked paid by an admin (no Stripe fee).
    paid_out_of_band: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    # Stripe's processing fee on the payment, when it could be read.
    stripe_fee: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow_naive, onupdate=utcnow_naive)


class StoreInvoiceLine(Base):
    """One line of a store invoice.

    kind=order lines snapshot the order as billed (the order itself may change
    later); monthly_fee and adjustment lines only have a description and amount.
    """

    __tablename__ = "store_invoice_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("store_invoices.id", ondelete="CASCADE"), index=True)
    # order | monthly_fee | adjustment
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    # Signed: an adjustment may be a credit.
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    order_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    order_day: Mapped[date | None] = mapped_column(Date, nullable=True)
    channel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    commission_bps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    commission: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    # Commission already taken through Stripe on this order; amount = commission - this.
    collected_online: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow_naive)
