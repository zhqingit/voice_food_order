"""one active menu per store; backfill S/M/L variants for items created after 0021

1. Keep only the most recently updated active menu per store, then add a
   partial unique index so a store can never have two active menus (the
   customer menu and voice bot load it with scalar_one_or_none).
2. Items created after 0021 by the seed, CSV import or menu-photo import got
   price_small/medium/large but no variant rows, so the voice bot charged the
   base price. Materialize Small/Medium/Large variants for items that have
   sized prices and no variants at all (same default rule as 0021). New
   writes keep them in sync via menu_service.sync_size_variants.

Revision ID: 0022_active_menu_size_variants
Revises: 0021_backfill_sml_variants
Create Date: 2026-10-01
"""
import sqlalchemy as sa
from alembic import op

revision = "0022_active_menu_size_variants"
down_revision = "0021_backfill_sml_variants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE menus m
           SET active = FALSE
         WHERE m.active
           AND m.id <> (
                SELECT m2.id FROM menus m2
                 WHERE m2.store_id = m.store_id AND m2.active
                 ORDER BY m2.updated_at DESC, m2.id
                 LIMIT 1
           )
        """
    )
    op.create_index(
        "uq_menus_one_active_per_store",
        "menus",
        ["store_id"],
        unique=True,
        postgresql_where=sa.text("active"),
    )
    op.execute(
        """
        WITH targets AS (
            SELECT mi.* FROM menu_items mi
             WHERE (mi.price_small IS NOT NULL OR mi.price_medium IS NOT NULL OR mi.price_large IS NOT NULL)
               AND NOT EXISTS (SELECT 1 FROM menu_item_variants v WHERE v.menu_item_id = mi.id)
        )
        INSERT INTO menu_item_variants
            (id, menu_item_id, name, price, availability, sort_order, is_default, created_at)
        SELECT gen_random_uuid(), t.id, s.name, s.price, TRUE, s.sort_order, s.is_default, NOW()
          FROM targets t
         CROSS JOIN LATERAL (VALUES
                ('Small',  t.price_small,  0, t.price_medium IS NULL),
                ('Medium', t.price_medium, 1, TRUE),
                ('Large',  t.price_large,  2, t.price_medium IS NULL AND t.price_small IS NULL)
             ) AS s(name, price, sort_order, is_default)
         WHERE s.price IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index("uq_menus_one_active_per_store", table_name="menus")
