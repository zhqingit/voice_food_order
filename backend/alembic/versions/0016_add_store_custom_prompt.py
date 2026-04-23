"""add custom_prompt_raw and custom_prompt_generated to stores

Revision ID: 0016_add_store_custom_prompt
Revises: 0015_add_store_is_published
Create Date: 2026-04-23
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_add_store_custom_prompt"
down_revision = "0015_add_store_is_published"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stores", sa.Column("custom_prompt_raw", sa.Text(), nullable=True))
    op.add_column("stores", sa.Column("custom_prompt_generated", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("stores", "custom_prompt_generated")
    op.drop_column("stores", "custom_prompt_raw")
