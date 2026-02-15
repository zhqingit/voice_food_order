"""add store profile fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-01-16

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stores", sa.Column("address_line1", sa.String(length=255), nullable=True))
    op.add_column("stores", sa.Column("address_line2", sa.String(length=255), nullable=True))
    op.add_column("stores", sa.Column("city", sa.String(length=100), nullable=True))
    op.add_column("stores", sa.Column("state", sa.String(length=100), nullable=True))
    op.add_column("stores", sa.Column("postal_code", sa.String(length=32), nullable=True))
    op.add_column("stores", sa.Column("country", sa.String(length=64), nullable=True))
    op.add_column("stores", sa.Column("timezone", sa.String(length=64), nullable=True))
    op.add_column("stores", sa.Column("allow_pickup", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column("stores", sa.Column("allow_delivery", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column("stores", sa.Column("min_order_amount", sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("stores", "min_order_amount")
    op.drop_column("stores", "allow_delivery")
    op.drop_column("stores", "allow_pickup")
    op.drop_column("stores", "timezone")
    op.drop_column("stores", "country")
    op.drop_column("stores", "postal_code")
    op.drop_column("stores", "state")
    op.drop_column("stores", "city")
    op.drop_column("stores", "address_line2")
    op.drop_column("stores", "address_line1")
