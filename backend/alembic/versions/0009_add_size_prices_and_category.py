"""Add size prices (small/medium/large) and category to menu_items.

Revision ID: 0009
Revises: 0008
"""

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("menu_items", sa.Column("category", sa.String(255), nullable=True))
    op.add_column("menu_items", sa.Column("price_small", sa.Numeric(10, 2), nullable=True))
    op.add_column("menu_items", sa.Column("price_medium", sa.Numeric(10, 2), nullable=True))
    op.add_column("menu_items", sa.Column("price_large", sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("menu_items", "price_large")
    op.drop_column("menu_items", "price_medium")
    op.drop_column("menu_items", "price_small")
    op.drop_column("menu_items", "category")
