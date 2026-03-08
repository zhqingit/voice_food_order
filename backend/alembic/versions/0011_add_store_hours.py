"""Add store_hours table.

Revision ID: 0011
Revises: 0010
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "store_hours",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("day_of_week", sa.SmallInteger, nullable=False),
        sa.Column("open_time", sa.Time, nullable=False, server_default="09:00:00"),
        sa.Column("close_time", sa.Time, nullable=False, server_default="21:00:00"),
        sa.Column("is_closed", sa.Boolean, nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_table("store_hours")
