"""Calendar months in the platform timezone (settings.store_default_timezone),
shared by reports, store invoices and promotion budgets."""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func

from app.core.config import settings


def shift_month(d: date, months: int) -> date:
    """The first day of the month `months` away from d's month."""
    index = d.year * 12 + d.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


def platform_today() -> date:
    return datetime.now(ZoneInfo(settings.store_default_timezone)).date()


def in_month(column, start: date, end: date):
    """SQL condition: a naive-UTC timestamp column falls in [start, end) in the platform timezone."""
    local = func.timezone(settings.store_default_timezone, func.timezone("UTC", column))
    return (local >= datetime.combine(start, datetime.min.time())) & (local < datetime.combine(end, datetime.min.time()))
