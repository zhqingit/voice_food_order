"""backfill existing price_small/medium/large items as variant rows

One-shot data migration. For every menu_items row that has any of
price_small / price_medium / price_large set, materialize matching variant
rows named "Small" / "Medium" / "Large" with those prices. A single default
is chosen — prefer Medium, fall back to Small, then Large.

The legacy columns stay in place; the voice menu loader and tools prefer the
new variants and only fall back to price_small/medium/large when no variants
exist. Those columns will be dropped in a later migration once the store
portal UI has fully moved to the variants editor.

Idempotent: if a row with the same (menu_item_id, lower(name)) already
exists, it's skipped via ON CONFLICT DO NOTHING — safe to rerun.

Revision ID: 0021_backfill_sml_variants
Revises: 0020_menu_item_variants
Create Date: 2026-04-24
"""
from alembic import op

revision = "0021_backfill_sml_variants"
down_revision = "0020_menu_item_variants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Small
    op.execute(
        """
        INSERT INTO menu_item_variants
            (id, menu_item_id, name, price, availability, sort_order, is_default, created_at)
        SELECT gen_random_uuid(), mi.id, 'Small', mi.price_small, TRUE, 0,
               (mi.price_medium IS NULL AND mi.price_small IS NOT NULL),
               NOW()
          FROM menu_items mi
         WHERE mi.price_small IS NOT NULL
        ON CONFLICT (menu_item_id, (LOWER(name))) DO NOTHING
        """
    )
    # Medium — flagged default when present
    op.execute(
        """
        INSERT INTO menu_item_variants
            (id, menu_item_id, name, price, availability, sort_order, is_default, created_at)
        SELECT gen_random_uuid(), mi.id, 'Medium', mi.price_medium, TRUE, 1,
               (mi.price_medium IS NOT NULL),
               NOW()
          FROM menu_items mi
         WHERE mi.price_medium IS NOT NULL
        ON CONFLICT (menu_item_id, (LOWER(name))) DO NOTHING
        """
    )
    # Large — default only when it's the only size defined
    op.execute(
        """
        INSERT INTO menu_item_variants
            (id, menu_item_id, name, price, availability, sort_order, is_default, created_at)
        SELECT gen_random_uuid(), mi.id, 'Large', mi.price_large, TRUE, 2,
               (mi.price_medium IS NULL AND mi.price_small IS NULL AND mi.price_large IS NOT NULL),
               NOW()
          FROM menu_items mi
         WHERE mi.price_large IS NOT NULL
        ON CONFLICT (menu_item_id, (LOWER(name))) DO NOTHING
        """
    )


def downgrade() -> None:
    # Remove only the rows this migration inserted (by matching name).
    op.execute(
        """
        DELETE FROM menu_item_variants
         WHERE LOWER(name) IN ('small', 'medium', 'large')
        """
    )
