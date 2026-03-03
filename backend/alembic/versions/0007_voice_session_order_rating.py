"""add order_id and rating to voice_sessions

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-03

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("voice_sessions", sa.Column("order_id", sa.UUID(), nullable=True))
    op.add_column("voice_sessions", sa.Column("rating", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_voice_sessions_order_id",
        "voice_sessions",
        "orders",
        ["order_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_voice_sessions_order_id", "voice_sessions", ["order_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_voice_sessions_order_id", table_name="voice_sessions")
    op.drop_constraint("fk_voice_sessions_order_id", "voice_sessions", type_="foreignkey")
    op.drop_column("voice_sessions", "rating")
    op.drop_column("voice_sessions", "order_id")
