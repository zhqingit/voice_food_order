"""Store invoices, as shown to admins and to the store billed."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class InvoiceLineOut(BaseModel):
    id: uuid.UUID
    kind: str  # order | monthly_fee | adjustment
    description: str
    amount: Decimal
    order_code: str | None
    order_day: date | None
    channel: str | None
    subtotal: Decimal | None  # pre-tax, after store discounts
    commission_bps: int | None
    commission: Decimal | None
    collected_online: Decimal | None


class InvoiceOut(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    store_name: str
    period: str  # YYYY-MM
    status: str  # draft | open | paid | void | uncollectible
    overdue: bool
    total: Decimal
    order_count: int
    due_date: date | None
    hosted_url: str | None
    pdf_url: str | None
    paid_out_of_band: bool
    sent_at: datetime | None
    paid_at: datetime | None
    created_at: datetime


class InvoiceDetailOut(InvoiceOut):
    lines: list[InvoiceLineOut]


class InvoiceGenerateRequest(BaseModel):
    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")


class InvoiceAdjustmentCreate(BaseModel):
    description: str = Field(min_length=1, max_length=255)
    # Positive adds to the bill, negative is a credit.
    amount: Decimal = Field(max_digits=10, decimal_places=2)
