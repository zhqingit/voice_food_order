"""init

Revision ID: 0001
Revises: 
Create Date: 2025-12-12

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stores",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
    )
    op.create_index("ix_stores_name", "stores", ["name"], unique=False)
    op.create_index("ix_stores_email", "stores", ["email"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "refresh_sessions",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("principal_type", sa.String(length=32), nullable=False),
        sa.Column("principal_id", sa.UUID(), nullable=False),
        sa.Column("aud", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("device_label", sa.String(length=128), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
    )
    op.create_index("ix_refresh_sessions_principal_id", "refresh_sessions", ["principal_id"], unique=False)
    op.create_index("ix_refresh_sessions_principal_type", "refresh_sessions", ["principal_type"], unique=False)
    op.create_index("ix_refresh_sessions_aud", "refresh_sessions", ["aud"], unique=False)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("replaced_by_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["refresh_sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_refresh_tokens_session_id", "refresh_tokens", ["session_id"], unique=False)
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_session_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.drop_index("ix_refresh_sessions_aud", table_name="refresh_sessions")
    op.drop_index("ix_refresh_sessions_principal_type", table_name="refresh_sessions")
    op.drop_index("ix_refresh_sessions_principal_id", table_name="refresh_sessions")
    op.drop_table("refresh_sessions")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_stores_email", table_name="stores")
    op.drop_index("ix_stores_name", table_name="stores")
    op.drop_table("stores")
