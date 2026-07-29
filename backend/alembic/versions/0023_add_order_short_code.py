"""add short_code + code_day to orders

Revision ID: 0023_add_order_short_code
Revises: 0022_add_store_delivery_geo
Create Date: 2026-06-15
"""
from __future__ import annotations

import secrets
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import sqlalchemy as sa
from alembic import op


revision = "0023_add_order_short_code"
down_revision = "0022_add_store_delivery_geo"
branch_labels = None
depends_on = None


# Voice-friendly alphabet — no I, L, O, 0, 1. Matches the runtime generator.
_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXY23456789"
_CODE_LEN = 5


def _gen_code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(_CODE_LEN))


def _local_day(created_at: datetime, tz_name: str | None) -> date:
    if tz_name:
        try:
            tz = ZoneInfo(tz_name)
        except ZoneInfoNotFoundError:
            tz = timezone.utc
    else:
        tz = timezone.utc
    # created_at is stored timezone-naive in UTC.
    aware = created_at.replace(tzinfo=timezone.utc)
    return aware.astimezone(tz).date()


def upgrade() -> None:
    op.add_column("orders", sa.Column("short_code", sa.String(length=8), nullable=True))
    op.add_column("orders", sa.Column("code_day", sa.Date(), nullable=True))

    # Backfill: for each existing order, compute code_day from created_at in the
    # store's tz, then assign a code unique within (store_id, code_day).
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            """
            SELECT o.id, o.store_id, o.created_at, s.timezone
            FROM orders o
            JOIN stores s ON s.id = o.store_id
            ORDER BY o.created_at ASC
            """
        )
    ).fetchall()

    used: dict[tuple, set[str]] = {}
    for row in rows:
        order_id, store_id, created_at, tz_name = row
        day = _local_day(created_at, tz_name)
        key = (store_id, day)
        bucket = used.setdefault(key, set())
        for _ in range(20):
            code = _gen_code()
            if code not in bucket:
                bucket.add(code)
                break
        else:
            # Astronomically unlikely with 30^5 ≈ 24M combos per bucket; use
            # a unique fallback so the migration always completes.
            code = _gen_code() + secrets.token_hex(1).upper()
            bucket.add(code)
        conn.execute(
            sa.text("UPDATE orders SET short_code = :c, code_day = :d WHERE id = :id"),
            {"c": code, "d": day, "id": order_id},
        )

    op.alter_column("orders", "short_code", existing_type=sa.String(length=8), nullable=False)
    op.alter_column("orders", "code_day", existing_type=sa.Date(), nullable=False)

    op.create_unique_constraint(
        "uq_orders_store_day_short_code",
        "orders",
        ["store_id", "code_day", "short_code"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_orders_store_day_short_code", "orders", type_="unique")
    op.drop_column("orders", "code_day")
    op.drop_column("orders", "short_code")
