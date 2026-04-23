"""add fulfillment_type and delivery_address to orders

Revision ID: 0018_add_order_fulfillment
Revises: 0017_store_custom_prompts_list
Create Date: 2026-04-23
"""
from alembic import op
import sqlalchemy as sa

revision = "0018_add_order_fulfillment"
down_revision = "0017_store_custom_prompts_list"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("fulfillment_type", sa.String(length=16), nullable=True))
    op.add_column("orders", sa.Column("delivery_address", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "delivery_address")
    op.drop_column("orders", "fulfillment_type")
