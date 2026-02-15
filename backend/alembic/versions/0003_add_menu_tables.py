"""add menu tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-01-22

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "menus",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("store_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_menus_store_id", "menus", ["store_id"], unique=False)
    op.create_index("ix_menus_store_id_version", "menus", ["store_id", "version"], unique=False)

    op.create_table(
        "menu_items",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("menu_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("availability", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("modifiers", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["menu_id"], ["menus.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_menu_items_menu_id", "menu_items", ["menu_id"], unique=False)
    op.create_index("ix_menu_items_name", "menu_items", ["name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_menu_items_name", table_name="menu_items")
    op.drop_index("ix_menu_items_menu_id", table_name="menu_items")
    op.drop_table("menu_items")

    op.drop_index("ix_menus_store_id_version", table_name="menus")
    op.drop_index("ix_menus_store_id", table_name="menus")
    op.drop_table("menus")
