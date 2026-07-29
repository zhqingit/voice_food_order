"""add latitude/longitude/delivery_radius_km to stores

Lets a store define a geographic delivery area. Coordinates are populated by
server-side geocoding of the store's address; delivery_radius_km is the
maximum straight-line distance (haversine) from the store at which a
customer delivery address will be accepted.

Revision ID: 0022_add_store_delivery_geo
Revises: 0021_backfill_sml_variants
Create Date: 2026-06-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0022_add_store_delivery_geo"
down_revision = "0021_backfill_sml_variants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stores", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("stores", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column("stores", sa.Column("delivery_radius_km", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("stores", "delivery_radius_km")
    op.drop_column("stores", "longitude")
    op.drop_column("stores", "latitude")
