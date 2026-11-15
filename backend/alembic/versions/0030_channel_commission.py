"""commission by channel, locked per order; application fee per payment

Revision ID: 0030_channel_commission
Revises: 0029_payments
Create Date: 2026-11-14

stores.platform_fee_bps (one override for all orders) becomes the app-order
override, and a phone-order override and a monthly fee are added. Orders get
the commission rate locked at creation plus the amount; payments record the
application fee Stripe took.

Existing orders keep the single rate they were placed under (the store's old
override, else the old 10% default).
"""
import sqlalchemy as sa
from alembic import op

revision = "0030_channel_commission"
down_revision = "0029_payments"
branch_labels = None
depends_on = None

OLD_DEFAULT_BPS = 1000


def upgrade() -> None:
    op.alter_column("stores", "platform_fee_bps", new_column_name="commission_app_bps")
    op.add_column("stores", sa.Column("commission_phone_bps", sa.Integer(), nullable=True))
    op.add_column("stores", sa.Column("monthly_fee", sa.Numeric(10, 2), nullable=False, server_default="0"))

    op.add_column("orders", sa.Column("commission_bps", sa.Integer(), nullable=True))
    op.add_column("orders", sa.Column("commission", sa.Numeric(10, 2), nullable=False, server_default="0"))
    op.add_column("payments", sa.Column("application_fee", sa.Numeric(10, 2), nullable=True))

    op.execute(
        f"""
        UPDATE orders o
        SET commission_bps = COALESCE(s.commission_app_bps, {OLD_DEFAULT_BPS}),
            commission = ROUND(o.subtotal * COALESCE(s.commission_app_bps, {OLD_DEFAULT_BPS}) / 10000.0, 2)
        FROM stores s
        WHERE s.id = o.store_id
        """
    )
    # Card charges made before this: Stripe took the old rate on the amount charged.
    op.execute(
        """
        UPDATE payments p
        SET application_fee = ROUND(p.amount * o.commission_bps / 10000.0, 2)
        FROM orders o
        WHERE o.id = p.order_id AND p.kind = 'charge' AND p.method = 'card'
        """
    )


def downgrade() -> None:
    op.drop_column("payments", "application_fee")
    op.drop_column("orders", "commission")
    op.drop_column("orders", "commission_bps")
    op.drop_column("stores", "monthly_fee")
    op.drop_column("stores", "commission_phone_bps")
    op.alter_column("stores", "commission_app_bps", new_column_name="platform_fee_bps")
