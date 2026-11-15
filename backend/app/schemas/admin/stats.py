from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

CostCategory = Literal["server", "phone_numbers", "domain", "other"]


class ChannelStats(BaseModel):
    orders: int = 0
    gmv: Decimal = Decimal("0.00")  # pre-tax subtotal of completed orders, after store discounts
    discounts: Decimal = Decimal("0.00")  # store-funded promotions
    commission: Decimal = Decimal("0.00")


class StoreMonthStats(BaseModel):
    store_id: uuid.UUID
    store_name: str
    app: ChannelStats
    phone: ChannelStats
    # Commission on these orders taken through Stripe, and what is left to invoice.
    commission_online: Decimal
    commission_to_invoice: Decimal
    monthly_fee: Decimal
    revenue: Decimal  # commission + monthly fee
    ai_cost: Decimal  # app sessions + phone calls
    phone_calls: int
    phone_minutes: int
    telephony_cost: Decimal  # estimated
    stripe_fees: Decimal
    invoice_fees: Decimal  # Stripe fees on this month's paid invoice
    costs: Decimal
    net: Decimal


class PlatformCostOut(BaseModel):
    id: uuid.UUID
    month: date
    category: str
    amount: Decimal
    note: str | None


class PlatformCostCreate(BaseModel):
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    category: CostCategory
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    note: str | None = Field(default=None, max_length=255)


class MonthTotals(BaseModel):
    orders: int
    gmv: Decimal
    discounts: Decimal
    commission: Decimal
    commission_online: Decimal
    commission_to_invoice: Decimal
    monthly_fees: Decimal
    revenue: Decimal
    ai_cost: Decimal
    telephony_cost: Decimal
    stripe_fees: Decimal
    invoice_fees: Decimal
    fixed_costs: Decimal
    costs: Decimal
    net: Decimal
    # This month's invoices to stores (sent ones).
    invoiced: Decimal
    invoice_paid: Decimal
    invoice_outstanding: Decimal  # open or uncollectible
    invoice_overdue: Decimal


class MonthlyStatsOut(BaseModel):
    month: str  # YYYY-MM
    totals: MonthTotals
    stores: list[StoreMonthStats]
    fixed_costs: list[PlatformCostOut]
