"""Move menu_items to store-level items pool + add menu_menu_items junction table.

Revision ID: 0008
Revises: 0007
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add store_id column to menu_items (nullable first for migration)
    op.add_column("menu_items", sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=True))

    # 2. Populate store_id from the menu's store_id
    op.execute(
        """
        UPDATE menu_items
        SET store_id = menus.store_id
        FROM menus
        WHERE menu_items.menu_id = menus.id
        """
    )

    # 3. Make store_id non-nullable
    op.alter_column("menu_items", "store_id", nullable=False)

    # 4. Add FK and index for store_id
    op.create_foreign_key(
        "fk_menu_items_store_id",
        "menu_items",
        "stores",
        ["store_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_menu_items_store_id", "menu_items", ["store_id"])

    # 5. Create the junction table
    op.create_table(
        "menu_menu_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("menu_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("menus.id", ondelete="CASCADE"), nullable=False),
        sa.Column("menu_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("menu_id", "menu_item_id", name="uq_menu_menu_items"),
    )
    op.create_index("ix_menu_menu_items_menu_id", "menu_menu_items", ["menu_id"])
    op.create_index("ix_menu_menu_items_menu_item_id", "menu_menu_items", ["menu_item_id"])

    # 6. Populate junction table from existing menu_id relationships
    op.execute(
        """
        INSERT INTO menu_menu_items (id, menu_id, menu_item_id)
        SELECT gen_random_uuid(), menu_id, id
        FROM menu_items
        WHERE menu_id IS NOT NULL
        """
    )

    # 7. Drop old menu_id FK and column
    op.drop_index("ix_menu_items_menu_id", table_name="menu_items")
    op.drop_constraint("menu_items_menu_id_fkey", "menu_items", type_="foreignkey")
    op.drop_column("menu_items", "menu_id")


def downgrade() -> None:
    # Re-add menu_id column
    op.add_column("menu_items", sa.Column("menu_id", postgresql.UUID(as_uuid=True), nullable=True))

    # Restore menu_id from junction table (pick first menu if item is in multiple)
    op.execute(
        """
        UPDATE menu_items
        SET menu_id = sub.menu_id
        FROM (
            SELECT DISTINCT ON (menu_item_id) menu_item_id, menu_id
            FROM menu_menu_items
            ORDER BY menu_item_id
        ) sub
        WHERE menu_items.id = sub.menu_item_id
        """
    )

    op.create_index("ix_menu_items_menu_id", "menu_items", ["menu_id"])
    op.create_foreign_key("menu_items_menu_id_fkey", "menu_items", "menus", ["menu_id"], ["id"], ondelete="CASCADE")

    # Drop junction table
    op.drop_table("menu_menu_items")

    # Drop store_id
    op.drop_index("ix_menu_items_store_id", table_name="menu_items")
    op.drop_constraint("fk_menu_items_store_id", "menu_items", type_="foreignkey")
    op.drop_column("menu_items", "store_id")
