"""add review to voice_sessions

Revision ID: 6a3bdef5c53c
Revises: 0014
Create Date: 2026-03-10 05:25:23.641449

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6a3bdef5c53c'
down_revision = '0014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('voice_sessions', sa.Column('review', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('voice_sessions', 'review')
