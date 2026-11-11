from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

import pytest

from app.models.store import Store
from app.models.store_hours import StoreHours
from app.services.store_hours_service import store_open_status

# 2026-11-09 is a Monday. Phoenix is UTC-7 all year (no DST).
MONDAY_NOON_PHX = datetime(2026, 11, 9, 19, 0, tzinfo=UTC)
PHOENIX = ZoneInfo("America/Phoenix")


def _phx(day, hour, minute=0):
    """A local Phoenix time on 2026-11-<day>."""
    return datetime(2026, 11, day, hour, minute, tzinfo=PHOENIX)


@pytest.fixture()
def store(session_factory):
    def _make(hours=None, timezone=None):
        with session_factory() as db:
            s = Store(name="Wok", email="wok@example.com", password_hash="x", timezone=timezone)
            db.add(s)
            db.flush()
            for day, (open_t, close_t, closed) in (hours or {}).items():
                db.add(StoreHours(store_id=s.id, day_of_week=day, open_time=open_t, close_time=close_t, is_closed=closed))
            db.commit()
            return s.id

    return _make


def _status(session_factory, store_id, now):
    with session_factory() as db:
        return store_open_status(db, db.get(Store, store_id), now=now)


def test_no_hours_means_unknown(session_factory, store):
    status = _status(session_factory, store(), MONDAY_NOON_PHX)

    assert status.is_open is None and status.today_text is None


def test_open_and_closed_during_a_normal_day(session_factory, store):
    store_id = store({0: (time(11), time(21, 30), False)})

    assert _status(session_factory, store_id, _phx(9, 12)).is_open is True
    assert _status(session_factory, store_id, _phx(9, 10, 59)).is_open is False
    late = _status(session_factory, store_id, _phx(9, 21, 30))
    assert late.is_open is False and late.today_text == "11 AM to 9:30 PM"


def test_closed_day_and_missing_day_are_closed(session_factory, store):
    store_id = store({0: (time(9), time(17), True)})

    monday = _status(session_factory, store_id, _phx(9, 12))
    tuesday = _status(session_factory, store_id, _phx(10, 12))

    assert (monday.is_open, monday.today_text) == (False, "closed")
    assert (tuesday.is_open, tuesday.today_text) == (False, "closed")


def test_late_shift_runs_past_midnight(session_factory, store):
    store_id = store({0: (time(18), time(2), False), 1: (time(18), time(2), False)})

    assert _status(session_factory, store_id, _phx(9, 23)).is_open is True
    # 1 AM Tuesday is still Monday's shift.
    assert _status(session_factory, store_id, _phx(10, 1)).is_open is True
    assert _status(session_factory, store_id, _phx(10, 3)).is_open is False


def test_store_timezone_is_used(session_factory, store):
    # Noon in Phoenix is 2 PM in New York; open 1-3 PM local.
    store_id = store({0: (time(13), time(15), False)}, timezone="America/New_York")

    assert _status(session_factory, store_id, MONDAY_NOON_PHX).is_open is True


def test_bad_timezone_falls_back_to_default(session_factory, store):
    store_id = store({0: (time(11), time(13), False)}, timezone="Mars/Olympus")

    assert _status(session_factory, store_id, MONDAY_NOON_PHX).is_open is True
