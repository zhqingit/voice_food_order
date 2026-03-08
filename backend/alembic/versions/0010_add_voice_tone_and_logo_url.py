"""Add voice_tone and logo_url to stores.

Revision ID: 0010
Revises: 0009
"""

from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stores", sa.Column("voice_tone", sa.String(32), nullable=True))
    op.add_column("stores", sa.Column("logo_url", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("stores", "logo_url")
    op.drop_column("stores", "voice_tone")
