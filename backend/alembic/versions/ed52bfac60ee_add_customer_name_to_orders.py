"""add customer_name to orders

Revision ID: ed52bfac60ee
Revises: 6a3bdef5c53c
Create Date: 2026-03-10 18:04:25.770966

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ed52bfac60ee'
down_revision = '6a3bdef5c53c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('orders', sa.Column('customer_name', sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column('orders', 'customer_name')
