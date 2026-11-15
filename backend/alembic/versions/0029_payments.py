"""payments: one row per charge or refund on an order

Revision ID: 0029_payments
Revises: 0028_order_events
Create Date: 2026-11-14

Backfills a succeeded charge for every order already marked paid, so totals
paid and refunds work for existing orders too.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0029_payments"
down_revision = "0028_order_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("stripe_id", sa.String(length=255), nullable=True, unique=True),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payments.id"), nullable=True),
        sa.Column("failure_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
    )
    op.create_index("ix_payments_order_id", "payments", ["order_id"])
    op.execute(
        """
        INSERT INTO payments (id, order_id, kind, method, amount, status, stripe_id, created_at, updated_at)
        SELECT gen_random_uuid(), id, 'charge',
               CASE WHEN payment_ref LIKE 'pi\\_%' THEN 'card' ELSE 'in_store' END,
               total, 'succeeded',
               CASE WHEN payment_ref LIKE 'pi\\_%' THEN payment_ref END,
               COALESCE(paid_at, created_at), COALESCE(paid_at, created_at)
        FROM orders
        WHERE payment_status = 'paid'
        """
    )


def downgrade() -> None:
    op.drop_index("ix_payments_order_id", table_name="payments")
    op.drop_table("payments")
