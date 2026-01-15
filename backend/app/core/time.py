from __future__ import annotations

from datetime import UTC, datetime


def utcnow_naive() -> datetime:
    """Return a naive datetime representing 'now' in UTC.

    We intentionally store naive UTC timestamps in the DB for cross-DB compatibility
    (e.g., sqlite tests vs Postgres). Using datetime.utcnow() is deprecated in
    Python 3.12+, so we derive it from an aware UTC datetime instead.
    """

    return datetime.now(UTC).replace(tzinfo=None)
