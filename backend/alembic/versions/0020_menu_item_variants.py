"""add menu_item_variants table and order_items.variant_name snapshot

Introduces a general variant model so items like Coke (12 Oz Can / 2 Liter)
or pizzas (10" / 14" / 18") can carry an arbitrary list of named, priced
options instead of being forced into the old price_small/price_medium/
price_large triple. The legacy columns are left in place for now; they'll
be dropped in a later migration after the backfill + UI cutover.

order_items.variant_name is a text snapshot (alongside price_snapshot), so
an order keeps a correct history even if the variant row is later renamed
or deleted.

Revision ID: 0020_menu_item_variants
Revises: 0018_add_order_fulfillment
Create Date: 2026-04-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0020_menu_item_variants"
down_revision = "0018_add_order_fulfillment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "menu_item_variants",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "menu_item_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("menu_items.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("availability", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=True),
    )
    # Case-insensitive uniqueness of variant name per menu item.
    op.create_index(
        "ux_menu_item_variants_item_name_lower",
        "menu_item_variants",
        ["menu_item_id", sa.text("LOWER(name)")],
        unique=True,
    )

    op.add_column(
        "order_items",
        sa.Column("variant_name", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("order_items", "variant_name")
    op.drop_index("ux_menu_item_variants_item_name_lower", table_name="menu_item_variants")
    op.drop_table("menu_item_variants")
