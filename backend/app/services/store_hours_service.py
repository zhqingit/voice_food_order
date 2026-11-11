"""Is a store open right now, by its weekly hours in its own timezone."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.store import Store
from app.models.store_hours import StoreHours


@dataclass(frozen=True)
class OpenStatus:
    # None when the store never set its hours: callers treat that as open.
    is_open: bool | None
    # Today's hours for speech, e.g. "11 AM to 9:30 PM" or "closed".
    today_text: str | None


def _store_zone(store: Store) -> ZoneInfo:
    for name in (store.timezone, settings.store_default_timezone):
        try:
            if name:
                return ZoneInfo(name.strip())
        except (ZoneInfoNotFoundError, ValueError):
            continue
    return ZoneInfo("UTC")


def _spoken_time(value: time) -> str:
    hour = value.hour % 12 or 12
    suffix = "AM" if value.hour < 12 else "PM"
    return f"{hour} {suffix}" if value.minute == 0 else f"{hour}:{value.minute:02d} {suffix}"


def _row_text(row: StoreHours | None) -> str:
    if row is None or row.is_closed:
        return "closed"
    return f"{_spoken_time(row.open_time)} to {_spoken_time(row.close_time)}"


def _overnight(row: StoreHours) -> bool:
    return row.close_time <= row.open_time


def store_open_status(db: Session, store: Store, *, now: datetime | None = None) -> OpenStatus:
    rows = {
        row.day_of_week: row
        for row in db.execute(select(StoreHours).where(StoreHours.store_id == store.id)).scalars()
    }
    if not rows:
        return OpenStatus(is_open=None, today_text=None)

    local = (now or datetime.now(UTC)).astimezone(_store_zone(store))
    clock = local.time().replace(tzinfo=None)
    today = rows.get(local.weekday())  # 0=Mon, same as store_hours
    yesterday = rows.get((local - timedelta(days=1)).weekday())

    is_open = False
    if today is not None and not today.is_closed:
        if _overnight(today):
            is_open = clock >= today.open_time
        else:
            is_open = today.open_time <= clock < today.close_time
    # Past midnight, still inside yesterday's late shift (e.g. 6 PM - 2 AM).
    if not is_open and yesterday is not None and not yesterday.is_closed and _overnight(yesterday):
        is_open = clock < yesterday.close_time
    return OpenStatus(is_open=is_open, today_text=_row_text(today))

