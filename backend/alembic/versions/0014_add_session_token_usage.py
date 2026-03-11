"""add token usage columns to voice_sessions

Revision ID: 0014
Revises: 0013
Create Date: 2026-03-09
"""

from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("voice_sessions", sa.Column("prompt_tokens", sa.Integer, nullable=False, server_default="0"))
    op.add_column("voice_sessions", sa.Column("completion_tokens", sa.Integer, nullable=False, server_default="0"))
    op.add_column("voice_sessions", sa.Column("total_tokens", sa.Integer, nullable=False, server_default="0"))
    op.add_column("voice_sessions", sa.Column("llm_cost", sa.Numeric(10, 6), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("voice_sessions", "llm_cost")
    op.drop_column("voice_sessions", "total_tokens")
    op.drop_column("voice_sessions", "completion_tokens")
    op.drop_column("voice_sessions", "prompt_tokens")
