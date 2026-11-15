"""monthly store invoices

Revision ID: 0032_store_invoices
Revises: 0031_cost_tracking
Create Date: 2026-11-14

store_invoices + store_invoice_lines hold the platform's monthly bill to each
store. orders.invoice_id marks which invoice billed an order, so it is never
billed twice; stores.stripe_customer_id is the Stripe Customer invoiced.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0032_store_invoices"
down_revision = "0031_cost_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "store_invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("total", sa.Numeric(10, 2), nullable=False),
        sa.Column("stripe_invoice_id", sa.String(255), nullable=True, unique=True),
        sa.Column("hosted_url", sa.Text(), nullable=True),
        sa.Column("pdf_url", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("paid_out_of_band", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("stripe_fee", sa.Numeric(10, 2), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
    )
    op.create_index("ix_store_invoices_store_id", "store_invoices", ["store_id"])
    op.create_index("ix_store_invoices_period", "store_invoices", ["period"])
    op.create_index(
        "uq_store_invoices_store_period_live",
        "store_invoices",
        ["store_id", "period"],
        unique=True,
        postgresql_where=sa.text("status <> 'void'"),
    )

    op.create_table(
        "store_invoice_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("store_invoices.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("order_code", sa.String(16), nullable=True),
        sa.Column("order_day", sa.Date(), nullable=True),
        sa.Column("channel", sa.String(32), nullable=True),
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=True),
        sa.Column("commission_bps", sa.Integer(), nullable=True),
        sa.Column("commission", sa.Numeric(10, 2), nullable=True),
        sa.Column("collected_online", sa.Numeric(10, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
    )
    op.create_index("ix_store_invoice_lines_invoice_id", "store_invoice_lines", ["invoice_id"])

    op.add_column(
        "orders",
        sa.Column(
            "invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("store_invoices.id", ondelete="SET NULL"), nullable=True
        ),
    )
    op.create_index("ix_orders_invoice_id", "orders", ["invoice_id"])
    op.add_column("stores", sa.Column("stripe_customer_id", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("stores", "stripe_customer_id")
    op.drop_index("ix_orders_invoice_id", table_name="orders")
    op.drop_column("orders", "invoice_id")
    op.drop_index("ix_store_invoice_lines_invoice_id", table_name="store_invoice_lines")
    op.drop_table("store_invoice_lines")
    op.drop_index("uq_store_invoices_store_period_live", table_name="store_invoices")
    op.drop_index("ix_store_invoices_period", table_name="store_invoices")
    op.drop_index("ix_store_invoices_store_id", table_name="store_invoices")
    op.drop_table("store_invoices")
