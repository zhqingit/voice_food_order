"""add is_published to stores

Revision ID: 0015
Revises: ed52bfac60ee
Create Date: 2026-03-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_add_store_is_published"
down_revision = "ed52bfac60ee"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stores", sa.Column("is_published", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("stores", "is_published")
