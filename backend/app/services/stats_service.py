"""Monthly revenue and cost report for the admin portal.

Revenue counts completed orders only, by the store-local day the order was
placed (orders.code_day). Costs count everything that happened in the month,
calls and sessions that ended without an order included, dated in the
platform timezone (settings.store_default_timezone).

Revenue per store: the commission on its orders plus its monthly fee.
Costs per store: AI usage (app sessions and phone calls), Twilio minutes
(estimated) and Stripe processing fees. Fixed platform costs are entered by
an admin and only appear in the totals.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.order import Order
from app.models.payment import Payment
from app.models.phone_call import PhoneCall
from app.models.platform_cost import PlatformCost
from app.models.store import Store
from app.models.voice_session import VoiceSession
from app.schemas.admin.stats import ChannelStats, MonthlyStatsOut, MonthTotals, PlatformCostOut, StoreMonthStats
from app.services import commission
from app.services.order_payments import REFUND_COUNTED

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def estimate_stripe_fee(amount: Decimal) -> Decimal:
    """Stripe's standard US card rate, for charges whose real fee wasn't fetched."""
    return (amount * Decimal("0.029") + Decimal("0.30")).quantize(CENT, rounding=ROUND_HALF_UP)


def parse_month(month: str) -> date:
    """'2026-11' → date(2026, 11, 1)."""
    year, mon = month.split("-")
    return date(int(year), int(mon), 1)


def _next_month(start: date) -> date:
    return date(start.year + start.month // 12, start.month % 12 + 1, 1)


def _in_month(column, start: date, end: date):
    """A naive-UTC timestamp column falls in [start, end) in the platform timezone."""
    local = func.timezone(settings.store_default_timezone, func.timezone("UTC", column))
    return (local >= datetime.combine(start, datetime.min.time())) & (local < datetime.combine(end, datetime.min.time()))


class _Acc:
    """Running totals for one store."""

    def __init__(self) -> None:
        self.app = ChannelStats()
        self.phone = ChannelStats()
        self.commission_online = ZERO
        self.ai_cost = Decimal("0")
        self.phone_calls = 0
        self.phone_seconds = 0
        self.telephony_cost = Decimal("0")
        self.stripe_fees = ZERO


def monthly_report(db: Session, month: str) -> MonthlyStatsOut:
    start = parse_month(month)
    end = _next_month(start)
    acc: dict[uuid.UUID, _Acc] = {}

    def get(store_id: uuid.UUID) -> _Acc:
        return acc.setdefault(store_id, _Acc())

    # Completed orders and the commission collected on each through Stripe.
    orders = db.execute(
        select(Order.id, Order.store_id, Order.channel, Order.subtotal, Order.commission)
        .where(Order.status == "completed")
        .where(Order.code_day >= start, Order.code_day < end)
    ).all()
    fee = func.coalesce(Payment.application_fee, 0)
    collected = dict(
        db.execute(
            select(
                Payment.order_id,
                func.sum(
                    case(
                        ((Payment.kind == "charge") & (Payment.status == "succeeded"), fee),
                        ((Payment.kind == "refund") & Payment.status.in_(REFUND_COUNTED), -fee),
                        else_=0,
                    )
                ),
            )
            .where(Payment.order_id.in_([o.id for o in orders]))
            .group_by(Payment.order_id)
        ).all()
    ) if orders else {}
    for o in orders:
        a = get(o.store_id)
        ch = a.phone if commission.is_phone(o.channel) else a.app
        ch.orders += 1
        ch.gmv += o.subtotal
        ch.commission += o.commission
        a.commission_online += min(max(Decimal(collected.get(o.id) or 0), ZERO), o.commission)

    # AI cost of app voice sessions (phone calls are counted from phone_calls).
    for store_id, cost in db.execute(
        select(VoiceSession.store_id, func.sum(VoiceSession.llm_cost))
        .where(VoiceSession.channel != commission.PHONE_CHANNEL)
        .where(_in_month(VoiceSession.started_at, start, end))
        .group_by(VoiceSession.store_id)
    ).all():
        get(store_id).ai_cost += cost or 0

    for store_id, calls, seconds, ai, telephony in db.execute(
        select(
            PhoneCall.store_id,
            func.count(),
            func.sum(PhoneCall.duration_seconds),
            func.sum(PhoneCall.ai_cost),
            func.sum(PhoneCall.telephony_cost),
        )
        .where(_in_month(PhoneCall.started_at, start, end))
        .group_by(PhoneCall.store_id)
    ).all():
        a = get(store_id)
        a.phone_calls += calls
        a.phone_seconds += seconds or 0
        a.ai_cost += ai or 0
        a.telephony_cost += telephony or 0

    # Stripe fees on card charges made this month (Stripe keeps them on refunds).
    for store_id, amount, stripe_fee in db.execute(
        select(Order.store_id, Payment.amount, Payment.stripe_fee)
        .join(Order, Order.id == Payment.order_id)
        .where(Payment.kind == "charge", Payment.method == "card", Payment.status == "succeeded")
        .where(_in_month(Payment.created_at, start, end))
    ).all():
        get(store_id).stripe_fees += stripe_fee if stripe_fee is not None else estimate_stripe_fee(amount)

    # Stores with a monthly fee are listed even in a month without activity.
    stores = {
        s.id: s
        for s in db.execute(select(Store).where(Store.id.in_(list(acc)) | (Store.monthly_fee > 0))).scalars()
    }
    rows = [_store_row(stores[sid], acc.get(sid) or _Acc()) for sid in stores]
    rows.sort(key=lambda r: (-r.revenue, r.store_name.lower()))

    fixed = db.execute(
        select(PlatformCost).where(PlatformCost.month == start).order_by(PlatformCost.created_at)
    ).scalars().all()
    return MonthlyStatsOut(
        month=start.strftime("%Y-%m"),
        totals=_totals(rows, fixed),
        stores=rows,
        fixed_costs=[cost_out(c) for c in fixed],
    )


def _store_row(store: Store, a: _Acc) -> StoreMonthStats:
    commission_total = a.app.commission + a.phone.commission
    monthly_fee = store.monthly_fee or ZERO
    revenue = commission_total + monthly_fee
    ai_cost = a.ai_cost.quantize(CENT, rounding=ROUND_HALF_UP)
    telephony = a.telephony_cost.quantize(CENT, rounding=ROUND_HALF_UP)
    costs = ai_cost + telephony + a.stripe_fees
    return StoreMonthStats(
        store_id=store.id,
        store_name=store.name,
        app=a.app,
        phone=a.phone,
        commission_online=a.commission_online,
        commission_to_invoice=commission_total - a.commission_online,
        monthly_fee=monthly_fee,
        revenue=revenue,
        ai_cost=ai_cost,
        phone_calls=a.phone_calls,
        phone_minutes=round(a.phone_seconds / 60),
        telephony_cost=telephony,
        stripe_fees=a.stripe_fees,
        costs=costs,
        net=revenue - costs,
    )


def _totals(rows: list[StoreMonthStats], fixed: list[PlatformCost]) -> MonthTotals:
    def total(fn) -> Decimal:
        return sum((fn(r) for r in rows), ZERO)

    fixed_costs = sum((c.amount for c in fixed), ZERO)
    revenue = total(lambda r: r.revenue)
    costs = total(lambda r: r.costs) + fixed_costs
    return MonthTotals(
        orders=sum(r.app.orders + r.phone.orders for r in rows),
        gmv=total(lambda r: r.app.gmv + r.phone.gmv),
        commission=total(lambda r: r.app.commission + r.phone.commission),
        commission_online=total(lambda r: r.commission_online),
        commission_to_invoice=total(lambda r: r.commission_to_invoice),
        monthly_fees=total(lambda r: r.monthly_fee),
        revenue=revenue,
        ai_cost=total(lambda r: r.ai_cost),
        telephony_cost=total(lambda r: r.telephony_cost),
        stripe_fees=total(lambda r: r.stripe_fees),
        fixed_costs=fixed_costs,
        costs=costs,
        net=revenue - costs,
    )


def cost_out(c: PlatformCost) -> PlatformCostOut:
    return PlatformCostOut(id=c.id, month=c.month, category=c.category, amount=c.amount, note=c.note)


CSV_HEADER = [
    "store", "app_orders", "app_gmv", "app_commission", "phone_orders", "phone_gmv", "phone_commission",
    "commission_online", "commission_to_invoice", "monthly_fee", "revenue",
    "ai_cost", "phone_calls", "phone_minutes", "telephony_cost", "stripe_fees", "costs", "net",
]


def csv_rows(report: MonthlyStatsOut) -> list[list]:
    body = [
        [
            r.store_name, r.app.orders, r.app.gmv, r.app.commission, r.phone.orders, r.phone.gmv, r.phone.commission,
            r.commission_online, r.commission_to_invoice, r.monthly_fee, r.revenue,
            r.ai_cost, r.phone_calls, r.phone_minutes, r.telephony_cost, r.stripe_fees, r.costs, r.net,
        ]
        for r in report.stores
    ]
    total = ["TOTAL", *(sum((row[i] for row in body), 0) for i in range(1, len(CSV_HEADER)))]
    t = report.totals
    return [CSV_HEADER, *body, total, ["fixed_costs", t.fixed_costs], ["net_after_fixed_costs", t.net]]
