import time
import uuid
from decimal import Decimal

import pytest

from app.core.errors import AppError
from app.models.order import Order
from app.models.store import Store
from app.models.user import User
from app.schemas.menu.menu import MenuItemCreate
from app.schemas.order.order import OrderCreate
from app.services import menu_service, order_service, voice_session_service
from app.voice.tool_router import VoiceToolContext, VoiceToolRouter, is_explicit_order_approval


@pytest.fixture()
def world(session_factory):
    """An orderable store with one sized item, plus two customers."""
    with session_factory() as db:
        store = Store(
            name="Test Kitchen", email="store@example.com", password_hash="x", is_published=True, is_approved=True
        )
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


def _confirm_name(router, name="Alice"):
    """set_customer_name, then simulate the bot finishing the read-back a while ago."""
    assert router.set_customer_name(name=name)["ok"]
    ctx = router._context
    ctx.name_set_at -= 5
    ctx.bot_speech_ended_at = ctx.name_set_at + 1


def _ask_and_hear(router, reply="Yes, place it."):
    """ask_to_place_order, then the bot says the question and the customer answers."""
    asked = router.ask_to_place_order()
    assert asked["ok"], asked
    ctx = router._context
    ctx.mark_bot_started_speaking()
    ctx.mark_bot_stopped_speaking()
    ctx.mark_customer_said(reply)
    return asked


def _ready_pickup_order(db_factory, world):
    router = _router(db_factory, world, user="alice")
    assert router.add_item(menu_item_id=world["item_id"], item_name=None, quantity=1)["ok"]
    assert router.set_fulfillment(type="pickup")["ok"]
    _confirm_name(router)
    return router


def _draft_order(db, world, *, user):
    return order_service.create_draft_order(
        db,
        payload=OrderCreate(store_id=world["store_id"], user_id=world[user], channel="voice", notes=None, items=[]),
    )


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
    alice_router._context.name_set_at = alice_router._context.bot_speech_ended_at = time.monotonic() - 5
    assert alice_router.ask_to_place_order()["ok"] is False
    assert alice_router.checkout()["ok"] is False

    with session_factory() as db:
        bobs_order = db.get(Order, bobs_order_id)
        assert bobs_order.status == "draft"
        assert bobs_order.customer_name is None
        assert bobs_order.subtotal == Decimal("10.00")


def test_checkout_requires_items_and_fulfillment(db_factory, world):
    router = _router(db_factory, world, user="alice")
    assert router.set_fulfillment(type="pickup")["ok"]

    _confirm_name(router)
    empty = router.checkout()
    assert empty["ok"] is False and "empty" in empty["message"].lower()

    router2 = _router(db_factory, world, user="alice")
    assert router2.add_item(menu_item_id=world["item_id"], item_name=None, quantity=1)["ok"]
    _confirm_name(router2)
    no_fulfillment = router2.checkout()
    assert no_fulfillment["ok"] is False and "set_fulfillment" in no_fulfillment["message"]

    assert router2.set_fulfillment(type="pickup")["ok"]
    _confirm_name(router2)
    _ask_and_hear(router2)
    assert router2.checkout()["ok"]


def test_submitted_order_cannot_be_changed(db_factory, world, session_factory):
    router = _router(db_factory, world, user="alice")
    added = router.add_item(menu_item_id=world["item_id"], item_name=None, quantity=1)
    order_item_id = uuid.UUID(added["order"]["items"][0]["order_item_id"])
    assert router.set_fulfillment(type="pickup")["ok"]
    _confirm_name(router)
    _ask_and_hear(router)
    assert router.checkout()["ok"]

    attempts = [
        router.add_item(menu_item_id=world["item_id"], item_name=None, quantity=1),
        router.remove_item(order_item_id=order_item_id, menu_item_id=None, item_name=None),
        router.update_item(order_item_id=order_item_id, quantity=5),
        router.set_order_note(note="extra spicy"),
        router.set_fulfillment(type="pickup"),
        router.confirm_delivery_address(),
        router.set_customer_name(name="Alice again"),
        router.ask_to_place_order(),
        router.checkout(),
    ]
    for result in attempts:
        assert result["ok"] is False, result

    with session_factory() as db:
        order = db.get(Order, router._context.order_id)
        assert order.status == "submitted"
        assert order.subtotal == Decimal("10.00")
        assert order.fulfillment_type == "pickup"
        assert order.customer_name == "Alice"


def test_asking_to_place_waits_for_answer_to_name_read_back(db_factory, world, session_factory):
    router = _router(db_factory, world, user="alice")
    assert router.add_item(menu_item_id=world["item_id"], item_name=None, quantity=1)["ok"]
    assert router.set_fulfillment(type="pickup")["ok"]
    ctx = router._context

    assert "set_customer_name" in router.ask_to_place_order()["message"]

    named = router.set_customer_name(name="  Alan ")
    assert named["read_back"] == "A, L, A, N"
    # Same model response as the read-back: the bot has not finished speaking.
    assert router.ask_to_place_order()["ok"] is False
    # Bot finished the read-back just now: chained right after it.
    ctx.mark_bot_stopped_speaking()
    assert router.ask_to_place_order()["ok"] is False
    # Customer answered: the read-back ended a few seconds before.
    ctx.name_set_at -= 3
    ctx.bot_speech_ended_at -= 3
    _ask_and_hear(router)
    assert router.checkout()["ok"]

    with session_factory() as db:
        order = db.get(Order, ctx.order_id)
        assert (order.status, order.customer_name) == ("submitted", "Alan")


def test_renaming_restarts_the_read_back_gate(db_factory, world):
    router = _router(db_factory, world, user="alice")
    assert router.add_item(menu_item_id=world["item_id"], item_name=None, quantity=1)["ok"]
    assert router.set_fulfillment(type="pickup")["ok"]
    _confirm_name(router, "Aram")

    assert router.set_customer_name(name="Alan")["ok"]  # customer corrected the name
    assert router.ask_to_place_order()["ok"] is False


@pytest.mark.parametrize(
    "reply,approved",
    [
        ("Yes.", True),
        ("Yeah, go ahead.", True),
        ("Okay, place the order.", True),
        ("Sure, thanks.", True),
        ("好的，下单吧", True),
        ("", False),
        ("No.", False),
        ("That's all.", False),
        ("What else do you have?", False),
        ("Yes, but add a Coke.", False),
        ("Okay, what else do you have", False),
        ("Yes, wait a second.", False),
        ("I don't think so, yes.", False),
        ("Alan.", False),
        ("540 North Mammoth Way.", False),
        ("Yesterday.", False),
        ("好的，还要一个可乐", False),
        ("可以吗", False),
    ],
)
def test_order_approval_needs_the_customers_clear_yes(reply, approved):
    assert is_explicit_order_approval(reply) is approved


def _assert_still_draft(session_factory, router):
    with session_factory() as db:
        assert db.get(Order, router._context.order_id).status == "draft"


def test_checkout_refused_without_asking(db_factory, world, session_factory):
    router = _ready_pickup_order(db_factory, world)
    router._context.mark_customer_said("Yes.")

    result = router.checkout()

    assert result["ok"] is False and "Should I place your order now?" in result["say"]
    _assert_still_draft(session_factory, router)

    # The refusal itself asked, so the bot saying it and a yes are enough.
    router._context.mark_bot_started_speaking()
    router._context.mark_bot_stopped_speaking()
    router._context.mark_customer_said("Yes.")
    assert router.checkout()["ok"]


def test_checkout_refused_before_the_customer_answers(db_factory, world, session_factory):
    router = _ready_pickup_order(db_factory, world)
    ctx = router._context
    assert router.ask_to_place_order()["ok"]

    assert router.checkout()["ok"] is False  # same model response as the question
    ctx.mark_bot_started_speaking()
    assert router.checkout()["ok"] is False  # still asking
    ctx.mark_customer_said("Yes.")  # talking over the question doesn't count
    ctx.mark_bot_stopped_speaking()
    assert router.checkout()["ok"] is False
    _assert_still_draft(session_factory, router)

    ctx.mark_customer_said("Yes.")
    assert router.checkout()["ok"]


def test_question_instead_of_yes_does_not_place_order(db_factory, world, session_factory):
    router = _ready_pickup_order(db_factory, world)
    _ask_and_hear(router, reply="What else do you have?")

    result = router.checkout()
    assert result["ok"] is False and "What else do you have?" in result["message"]

    # A later "yes" doesn't count until the bot has asked again.
    router._context.mark_customer_said("Yes.")
    assert router.checkout()["ok"] is False
    _assert_still_draft(session_factory, router)

    _ask_and_hear(router)
    assert router.checkout()["ok"]


def test_yes_to_something_said_after_the_question_does_not_count(db_factory, world, session_factory):
    router = _ready_pickup_order(db_factory, world)
    ctx = router._context
    assert router.ask_to_place_order()["ok"]
    ctx.mark_bot_started_speaking()
    ctx.mark_bot_stopped_speaking()
    # Silence nudge: "Anything else I can get you?"
    ctx.mark_bot_started_speaking()
    ctx.mark_bot_stopped_speaking()
    ctx.mark_customer_said("Yes.")

    assert router.checkout()["ok"] is False
    _assert_still_draft(session_factory, router)


@pytest.mark.parametrize("change", ["add_item", "set_fulfillment", "set_customer_name"])
def test_changing_the_order_requires_asking_again(db_factory, world, session_factory, change):
    router = _ready_pickup_order(db_factory, world)
    _ask_and_hear(router)

    if change == "add_item":
        assert router.add_item(menu_item_id=world["item_id"], item_name=None, quantity=2, variant="Large")["ok"]
    elif change == "set_fulfillment":
        assert router.set_fulfillment(type="pickup")["ok"]
    else:
        assert router.set_customer_name(name="Bob")["ok"]

    assert router.checkout()["ok"] is False
    _assert_still_draft(session_factory, router)


def test_total_changed_outside_the_call_requires_asking_again(db_factory, world, session_factory):
    from app.models.order_item import OrderItem

    router = _ready_pickup_order(db_factory, world)
    _ask_and_hear(router)
    with session_factory() as db:  # e.g. edited in the app while on the call
        item = db.query(OrderItem).filter(OrderItem.order_id == router._context.order_id).one()
        item.quantity = 3
        db.commit()

    result = router.checkout()
    assert result["ok"] is False and "changed" in result["message"]
    _assert_still_draft(session_factory, router)


def test_ws_ownership_checks(session_factory, world):
    with session_factory() as db:
        session = voice_session_service.create_session(
            db, store_id=world["store_id"], user_id=world["bob"], channel="voice"
        )
        order = _draft_order(db, world, user="bob")
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


@pytest.mark.parametrize("field,value,status", [("is_published", False, 410), ("is_approved", False, 404)])
def test_store_must_be_orderable(session_factory, world, field, value, status):
    with session_factory() as db:
        store = db.get(Store, world["store_id"])
        setattr(store, field, value)
        db.commit()
        with pytest.raises(AppError) as exc:
            voice_session_service.get_orderable_store(db, store_id=world["store_id"])
        assert exc.value.status_code == status


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
        bobs_order = _draft_order(db, world, user="bob")
        db.commit()
        foreign = [{"session_id": bobs_session.id}, {"order_id": bobs_order.id}]

    alice_token = create_access_token(subject=str(world["alice"]), role=PrincipalType.user, audience=Audience.mobile)
    headers = {"Authorization": f"Bearer {alice_token}"}
    for params in foreign:
        with pytest.raises(WebSocketDisconnect) as exc:
            with user_client.websocket_connect(_ws_url(world, **params), headers=headers):
                pass
        assert exc.value.code == 1008, params


def test_delivery_saves_googles_spelling_and_read_back(db_factory, world, session_factory, monkeypatch):
    from app.services import delivery_service

    monkeypatch.setattr(
        delivery_service,
        "is_within_delivery_range",
        lambda store, address: delivery_service.RangeCheck(True, 3.0, "ok", "540 N Mammoth Way, Chandler, AZ 85225"),
    )
    router = _router(db_factory, world, user="alice")
    result = router.set_fulfillment(type="delivery", delivery_address="540 N Mamas Way, Chandler, AZ")

    assert result["ok"], result
    assert result["read_back"] == "540 North M, A, M, M, O, T, H Way, Chandler"
    with session_factory() as db:
        assert db.get(Order, router._context.order_id).delivery_address == "540 N Mammoth Way, Chandler, AZ 85225"


def _start_call(client, world, *, secret=None, **overrides):
    payload = {"room_url": "https://example.daily.co/room", "token": "daily-token", "store_id": str(world["store_id"]), **overrides}
    headers = {"X-Telephony-Secret": secret} if secret else {}
    return client.post("/voice/telephony/daily/start", json=payload, headers=headers)


def test_telephony_start_is_disabled_without_secret(user_client, world, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "telephony_shared_secret", None)
    assert _start_call(user_client, world, secret="anything").status_code == 404


def test_telephony_start_requires_secret_and_orderable_store(user_client, session_factory, db_factory, world, monkeypatch):
    from app.api.routers.voice import telephony
    from app.core.config import settings

    secret = "t" * 40
    monkeypatch.setattr(settings, "telephony_shared_secret", secret)
    monkeypatch.setattr(telephony, "get_db_session", db_factory)

    assert _start_call(user_client, world).status_code == 401
    assert _start_call(user_client, world, secret="wrong" * 8).status_code == 401

    with session_factory() as db:
        bobs_order_id = _draft_order(db, world, user="bob").id
        db.commit()
    foreign = _start_call(user_client, world, secret=secret, user_id=str(world["alice"]), order_id=str(bobs_order_id))
    assert foreign.status_code == 404

    with session_factory() as db:
        db.get(Store, world["store_id"]).is_published = False
        db.commit()
    assert _start_call(user_client, world, secret=secret).status_code == 410
