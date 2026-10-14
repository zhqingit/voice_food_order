import uuid
from decimal import Decimal

import pytest

from app.core.errors import AppError
from app.models.order import Order
from app.models.store import Store
from app.models.user import User
from app.schemas.menu.menu import MenuItemCreate
from app.services import menu_service, voice_session_service
from app.voice.tool_router import VoiceToolContext, VoiceToolRouter


@pytest.fixture()
def world(session_factory):
    """A published store with one sized item, plus two customers."""
    with session_factory() as db:
        store = Store(name="Test Kitchen", email="store@example.com", password_hash="x", is_published=True)
        alice = User(email="alice@example.com", password_hash="x")
        bob = User(email="bob@example.com", password_hash="x")
        db.add_all([store, alice, bob])
        db.flush()
        item = menu_service.create_store_item(
            db,
            store_id=store.id,
            payload=MenuItemCreate(
                name="Fried Rice",
                price=Decimal("10.00"),
                price_small=Decimal("8.00"),
                price_medium=Decimal("10.00"),
                price_large=Decimal("12.00"),
            ),
        )
        db.commit()
        return {"store_id": store.id, "alice": alice.id, "bob": bob.id, "item_id": item.id}


def _router(db_factory, world, *, user, order_id=None):
    ctx = VoiceToolContext(
        db_factory=db_factory, store_id=world["store_id"], user_id=world[user], order_id=order_id
    )
    return VoiceToolRouter(ctx)


def test_sized_item_has_variants_and_charges_chosen_size(db_factory, world):
    router = _router(db_factory, world, user="alice")

    result = router.add_item(menu_item_id=world["item_id"], item_name=None, quantity=1, variant="Large")

    assert result["ok"], result
    assert result["order"]["subtotal"] == 12.0
    assert result["order"]["items"][0]["variant"] == "Large"


def test_sized_item_without_choice_uses_default_medium(db_factory, world):
    router = _router(db_factory, world, user="alice")

    result = router.add_item(menu_item_id=world["item_id"], item_name=None, quantity=2)

    assert result["ok"], result
    assert result["order"]["subtotal"] == 20.0


def test_tools_ignore_another_users_order(db_factory, world, session_factory):
    bob_router = _router(db_factory, world, user="bob")
    assert bob_router.add_item(menu_item_id=world["item_id"], item_name=None, quantity=1)["ok"]
    bobs_order_id = bob_router._context.order_id

    # Alice's client sends Bob's order id: tools must not see or touch it.
    alice_router = _router(db_factory, world, user="alice", order_id=bobs_order_id)
    assert alice_router.get_summary()["order"] is None
    assert alice_router.remove_item(order_item_id=None, menu_item_id=world["item_id"], item_name=None)["ok"] is False
    assert alice_router.checkout(customer_name="Mallory")["ok"] is False

    with session_factory() as db:
        bobs_order = db.get(Order, bobs_order_id)
        assert bobs_order.status == "draft"
        assert bobs_order.customer_name is None
        assert bobs_order.subtotal == Decimal("10.00")


def test_checkout_requires_items_and_fulfillment(db_factory, world):
    router = _router(db_factory, world, user="alice")
    assert router.set_fulfillment(type="pickup")["ok"]

    empty = router.checkout(customer_name="Alice")
    assert empty["ok"] is False and "empty" in empty["message"].lower()

    router2 = _router(db_factory, world, user="alice")
    assert router2.add_item(menu_item_id=world["item_id"], item_name=None, quantity=1)["ok"]
    no_fulfillment = router2.checkout(customer_name="Alice")
    assert no_fulfillment["ok"] is False and "set_fulfillment" in no_fulfillment["message"]

    assert router2.set_fulfillment(type="pickup")["ok"]
    assert router2.checkout(customer_name="Alice")["ok"]


def test_submitted_order_cannot_be_changed(db_factory, world, session_factory):
    router = _router(db_factory, world, user="alice")
    added = router.add_item(menu_item_id=world["item_id"], item_name=None, quantity=1)
    order_item_id = uuid.UUID(added["order"]["items"][0]["order_item_id"])
    assert router.set_fulfillment(type="pickup")["ok"]
    assert router.checkout(customer_name="Alice")["ok"]

    attempts = [
        router.add_item(menu_item_id=world["item_id"], item_name=None, quantity=1),
        router.remove_item(order_item_id=order_item_id, menu_item_id=None, item_name=None),
        router.update_item(order_item_id=order_item_id, quantity=5),
        router.set_order_note(note="extra spicy"),
        router.set_fulfillment(type="delivery", delivery_address="1 Main St"),
        router.checkout(customer_name="Alice again"),
    ]
    for result in attempts:
        assert result["ok"] is False, result

    with session_factory() as db:
        order = db.get(Order, router._context.order_id)
        assert order.status == "submitted"
        assert order.subtotal == Decimal("10.00")
        assert order.fulfillment_type == "pickup"


def test_ws_ownership_checks(session_factory, world):
    with session_factory() as db:
        session = voice_session_service.create_session(
            db, store_id=world["store_id"], user_id=world["bob"], channel="voice"
        )
        order = Order(store_id=world["store_id"], user_id=world["bob"], channel="voice", status="draft")
        db.add(order)
        db.commit()

        ids = {"store_id": world["store_id"]}
        assert voice_session_service.get_owned_session(db, session_id=session.id, user_id=world["bob"], **ids)
        assert voice_session_service.get_owned_draft_order(db, order_id=order.id, user_id=world["bob"], **ids)

        with pytest.raises(AppError) as exc:
            voice_session_service.get_owned_session(db, session_id=session.id, user_id=world["alice"], **ids)
        assert exc.value.status_code == 404
        with pytest.raises(AppError) as exc:
            voice_session_service.get_owned_draft_order(db, order_id=order.id, user_id=world["alice"], **ids)
        assert exc.value.status_code == 404

        order.status = "submitted"
        db.commit()
        with pytest.raises(AppError) as exc:
            voice_session_service.get_owned_draft_order(db, order_id=order.id, user_id=world["bob"], **ids)
        assert exc.value.status_code == 409


def test_unpublished_store_is_not_orderable(session_factory, world):
    with session_factory() as db:
        store = db.get(Store, world["store_id"])
        store.is_published = False
        db.commit()
        with pytest.raises(AppError) as exc:
            voice_session_service.get_orderable_store(db, store_id=world["store_id"])
        assert exc.value.status_code == 410


def _ws_url(world, **params):
    query = "&".join(f"{k}={v}" for k, v in {"store_id": world["store_id"], **params}.items())
    # Absolute URL: TestClient otherwise connects to ws://testserver, which the
    # host policy rejects before ownership is even checked.
    return f"ws://user-api.local/voice/ws?{query}"


def test_ws_rejects_foreign_session_and_order(user_client, session_factory, db_factory, world, monkeypatch):
    from starlette.websockets import WebSocketDisconnect

    from app.api.routers.voice import ws as ws_module
    from app.core.security import create_access_token
    from app.schemas.common import Audience, PrincipalType

    monkeypatch.setattr(ws_module, "get_db_session", db_factory)
    with session_factory() as db:
        bobs_session = voice_session_service.create_session(
            db, store_id=world["store_id"], user_id=world["bob"], channel="voice"
        )
        bobs_order = Order(store_id=world["store_id"], user_id=world["bob"], channel="voice", status="draft")
        db.add(bobs_order)
        db.commit()
        foreign = [{"session_id": bobs_session.id}, {"order_id": bobs_order.id}]

    alice_token = create_access_token(subject=str(world["alice"]), role=PrincipalType.user, audience=Audience.mobile)
    headers = {"Authorization": f"Bearer {alice_token}"}
    for params in foreign:
        with pytest.raises(WebSocketDisconnect) as exc:
            with user_client.websocket_connect(_ws_url(world, **params), headers=headers):
                pass
        assert exc.value.code == 1008, params
