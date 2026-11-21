"""store tax rate may be empty until entered

Revision ID: 0035_store_tax_rate_optional
Revises: 0034_platform_promotions
Create Date: 2026-11-20

New stores start with no tax rate and must enter one (0 allowed) before they
can publish. Existing stores keep their current rate.
"""
import sqlalchemy as sa
from alembic import op

revision = "0035_store_tax_rate_optional"
down_revision = "0034_platform_promotions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("stores", "tax_rate", existing_type=sa.Numeric(5, 4), nullable=True, server_default=None)


def downgrade() -> None:
    op.execute("UPDATE stores SET tax_rate = 0 WHERE tax_rate IS NULL")
    op.alter_column("stores", "tax_rate", existing_type=sa.Numeric(5, 4), nullable=False)
