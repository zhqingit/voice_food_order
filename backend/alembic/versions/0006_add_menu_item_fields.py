"""add alias_name, ingredient, note to menu_items

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-03

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("menu_items", sa.Column("alias_name", sa.String(255), nullable=True))
    op.add_column("menu_items", sa.Column("ingredient", sa.String(512), nullable=True))
    op.add_column("menu_items", sa.Column("note", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("menu_items", "note")
    op.drop_column("menu_items", "ingredient")
    op.drop_column("menu_items", "alias_name")
