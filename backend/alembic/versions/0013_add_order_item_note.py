"""add note column to order_items

Revision ID: 0013
Revises: 0012
Create Date: 2026-03-09
"""

from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "order_items",
        sa.Column("note", sa.String(512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("order_items", "note")
