"""platform promotions (funded from commission, online payments only)

Revision ID: 0034_platform_promotions
Revises: 0033_promotions
Create Date: 2026-11-14

A promotion with no store is a platform promotion. It gets optional limits
(first order only, uses per customer, monthly budget). Orders record the
platform promotion and the discount taken; card charges record theirs.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0034_platform_promotions"
down_revision = "0033_promotions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("promotions", "store_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.add_column("promotions", sa.Column("first_order_only", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("promotions", sa.Column("per_user_limit", sa.Integer(), nullable=True))
    op.add_column("promotions", sa.Column("monthly_budget", sa.Numeric(10, 2), nullable=True))
    op.add_column(
        "orders",
        sa.Column("platform_promotion_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("promotions.id"), nullable=True),
    )
    op.add_column("orders", sa.Column("platform_discount", sa.Numeric(10, 2), nullable=False, server_default="0"))
    op.add_column("payments", sa.Column("platform_discount", sa.Numeric(10, 2), nullable=True))
    op.add_column(
        "payments",
        sa.Column("platform_promotion_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("promotions.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("payments", "platform_promotion_id")
    op.drop_column("payments", "platform_discount")
    op.drop_column("orders", "platform_discount")
    op.drop_column("orders", "platform_promotion_id")
    op.drop_column("promotions", "monthly_budget")
    op.drop_column("promotions", "per_user_limit")
    op.drop_column("promotions", "first_order_only")
    op.execute("DELETE FROM promotions WHERE store_id IS NULL")
    op.alter_column("promotions", "store_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
