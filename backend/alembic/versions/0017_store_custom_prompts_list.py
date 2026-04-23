"""replace custom_prompt text columns with a list JSONB column

Revision ID: 0017_store_custom_prompts_list
Revises: 0016_add_store_custom_prompt
Create Date: 2026-04-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0017_store_custom_prompts_list"
down_revision = "0016_add_store_custom_prompt"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "stores",
        sa.Column("custom_prompts", JSONB, nullable=False, server_default="[]"),
    )
    op.drop_column("stores", "custom_prompt_generated")
    op.drop_column("stores", "custom_prompt_raw")


def downgrade() -> None:
    op.add_column("stores", sa.Column("custom_prompt_raw", sa.Text(), nullable=True))
    op.add_column("stores", sa.Column("custom_prompt_generated", sa.Text(), nullable=True))
    op.drop_column("stores", "custom_prompts")
