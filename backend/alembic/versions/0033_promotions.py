"""store promotions; order discount

Revision ID: 0033_promotions
Revises: 0032_store_invoices
Create Date: 2026-11-14

Stores create promotions (percent off, or dollars off over a minimum). An
order records the promotion it got and the discount, which comes off the
subtotal before tax and commission. Existing orders have no discount.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0033_promotions"
down_revision = "0032_store_invoices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "promotions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("value", sa.Numeric(10, 2), nullable=False),
        sa.Column("min_subtotal", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("channels", sa.String(8), nullable=False, server_default="all"),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
    )
    op.create_index("ix_promotions_store_id", "promotions", ["store_id"])
    op.add_column("orders", sa.Column("promotion_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("promotions.id"), nullable=True))
    op.add_column("orders", sa.Column("discount", sa.Numeric(10, 2), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("orders", "discount")
    op.drop_column("orders", "promotion_id")
    op.drop_index("ix_promotions_store_id", table_name="promotions")
    op.drop_table("promotions")
