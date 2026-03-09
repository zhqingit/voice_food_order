"""add store tax_rate

Revision ID: 0012
Revises: 0011
Create Date: 2026-03-08
"""

from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "stores",
        sa.Column("tax_rate", sa.Numeric(5, 4), nullable=False, server_default="0.0000"),
    )


def downgrade() -> None:
    op.drop_column("stores", "tax_rate")
