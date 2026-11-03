from sqlalchemy import select

from app import seed as seed_module
from app.models.menu_item import MenuItem
from app.models.menu_item_variant import MenuItemVariant
from app.models.store import Store


def test_seed_store_needs_approval_and_is_idempotent(session_factory, monkeypatch):
    monkeypatch.setattr(seed_module, "SessionLocal", session_factory)
    seed_module.seed()
    seed_module.seed()

    with session_factory() as db:
        store = db.execute(select(Store).where(Store.email == seed_module.TEST_STORE_EMAIL)).scalar_one()
        assert store.is_approved is False
        assert store.is_published is False

        items = db.execute(select(MenuItem).where(MenuItem.store_id == store.id)).scalars().all()
        assert len(items) == len(seed_module.DEMO_MENU_ITEMS)
        sized = next(i for i in items if i.price_small is not None)
        variants = db.execute(select(MenuItemVariant).where(MenuItemVariant.menu_item_id == sized.id)).scalars().all()
        assert variants
