"""add delivery_confirmed_at to orders

Revision ID: 0024_add_addr_confirmed_at
Revises: 0023_add_order_short_code
Create Date: 2026-06-15
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0024_add_addr_confirmed_at"
down_revision = "0023_add_order_short_code"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("delivery_confirmed_at", sa.DateTime(timezone=False), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("orders", "delivery_confirmed_at")
