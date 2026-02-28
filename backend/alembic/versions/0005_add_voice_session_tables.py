"""add voice session tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-01-22

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "voice_sessions",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("store_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=False), nullable=True),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_voice_sessions_store_id", "voice_sessions", ["store_id"], unique=False)
    op.create_index("ix_voice_sessions_user_id", "voice_sessions", ["user_id"], unique=False)
    op.create_index("ix_voice_sessions_status", "voice_sessions", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_voice_sessions_status", table_name="voice_sessions")
    op.drop_index("ix_voice_sessions_user_id", table_name="voice_sessions")
    op.drop_index("ix_voice_sessions_store_id", table_name="voice_sessions")
    op.drop_table("voice_sessions")
