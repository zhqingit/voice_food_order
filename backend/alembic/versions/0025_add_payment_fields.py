"""add payment/marketplace fields (orders, stores) and admins table

Revision ID: 0025_add_payment_fields
Revises: 0024_add_addr_confirmed_at
Create Date: 2026-07-30
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0025_add_payment_fields"
down_revision = "0024_add_addr_confirmed_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Orders: payment tracking, orthogonal to `status`.
    op.add_column(
        "orders",
        sa.Column("payment_status", sa.String(length=16), nullable=False, server_default="unpaid"),
    )
    op.add_column("orders", sa.Column("payment_ref", sa.String(length=255), nullable=True))
    op.add_column("orders", sa.Column("paid_at", sa.DateTime(timezone=False), nullable=True))

    # Stores: Stripe Connect (Express) linkage + marketplace controls.
    op.add_column("stores", sa.Column("stripe_account_id", sa.String(length=255), nullable=True))
    op.add_column(
        "stores",
        sa.Column("stripe_charges_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "stores",
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    # Per-store commission override in basis points; NULL falls back to the
    # platform default (settings.platform_fee_bps).
    op.add_column("stores", sa.Column("platform_fee_bps", sa.Integer(), nullable=True))

    # Admins: platform operators (third auth role). No self-signup.
    op.create_table(
        "admins",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
    )
    op.create_index("ix_admins_email", "admins", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_admins_email", table_name="admins")
    op.drop_table("admins")

    op.drop_column("stores", "platform_fee_bps")
    op.drop_column("stores", "is_approved")
    op.drop_column("stores", "stripe_charges_enabled")
    op.drop_column("stores", "stripe_account_id")

    op.drop_column("orders", "paid_at")
    op.drop_column("orders", "payment_ref")
    op.drop_column("orders", "payment_status")
