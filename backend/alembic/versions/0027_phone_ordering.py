"""phone ordering: per-store AI line, staff transfer number, caller number on orders

stores.phone_ai_number is the Twilio number that routes calls to this store
(admin-assigned, unique). phone_ai_enabled is the store's on/off switch and
phone_staff_number is where callers are transferred to a person.
orders.customer_phone records the caller's number for phone orders.

Revision ID: 0027_phone_ordering
Revises: 0026_active_menu_size_variants
Create Date: 2026-11-10
"""
import sqlalchemy as sa
from alembic import op

revision = "0027_phone_ordering"
down_revision = "0026_active_menu_size_variants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stores", sa.Column("phone_ai_number", sa.String(length=20), nullable=True))
    op.add_column(
        "stores",
        sa.Column("phone_ai_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("stores", sa.Column("phone_staff_number", sa.String(length=20), nullable=True))
    op.create_index("uq_stores_phone_ai_number", "stores", ["phone_ai_number"], unique=True)
    op.add_column("orders", sa.Column("customer_phone", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "customer_phone")
    op.drop_index("uq_stores_phone_ai_number", table_name="stores")
    op.drop_column("stores", "phone_staff_number")
    op.drop_column("stores", "phone_ai_enabled")
    op.drop_column("stores", "phone_ai_number")
