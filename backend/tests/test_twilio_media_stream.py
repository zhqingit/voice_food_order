import json
import uuid
from decimal import Decimal

import pytest
from starlette.websockets import WebSocketDisconnect

from app.api.routers.voice import twilio as twilio_module
from app.core.config import settings
from app.core.twilio import create_stream_token
from app.models.order import Order
from app.models.store import Store
from app.schemas.menu.menu import MenuItemCreate
from app.services import menu_service
from app.voice.tool_router import VoiceToolContext, VoiceToolRouter

CALLER = "+14805551234"
WS_URL = "ws://user-api.local/voice/telephony/twilio/ws"


@pytest.fixture(autouse=True)
def twilio_settings(monkeypatch, db_factory):
    monkeypatch.setattr(settings, "public_base_url", "https://voxeats.example.com")
    monkeypatch.setattr(settings, "telephony_twilio_auth_token", "twilio-test-auth-token")
    monkeypatch.setattr(settings, "telephony_twilio_account_sid", "AC" + "0" * 32)
    monkeypatch.setattr(twilio_module, "get_db_session", db_factory)


@pytest.fixture()
def store(session_factory):
    with session_factory() as db:
        store = Store(
            name="Hot Wok", email="wok@example.com", password_hash="x",
            is_approved=True, is_published=True, phone_ai_number="+16232943370", phone_ai_enabled=True,
        )
        db.add(store)
        db.flush()
        item = menu_service.create_store_item(
            db, store_id=store.id, payload=MenuItemCreate(name="Fried Rice", price=Decimal("10.00"))
        )
        db.commit()
        return {"id": store.id, "item_id": item.id}


def _start_messages(token, *, call_sid="CA123"):
    return [
        {"event": "connected", "protocol": "Call", "version": "1.0.0"},
        {
            "event": "start",
            "streamSid": "MZ123",
            "start": {"streamSid": "MZ123", "callSid": call_sid, "customParameters": {"token": token}},
        },
    ]


def _close_code(user_client, messages):
    with pytest.raises(WebSocketDisconnect) as exc:
        with user_client.websocket_connect(WS_URL) as ws:
            for message in messages:
                ws.send_text(json.dumps(message))
            ws.receive_text()
    return exc.value.code


def _token(store_id, call_sid="CA123"):
    return create_stream_token(store_id=store_id, call_sid=call_sid, caller=CALLER)


def test_stream_with_bad_token_is_closed(user_client, store):
    assert _close_code(user_client, _start_messages("not-a-token")) == 1008


def test_token_for_another_call_is_refused(user_client, store):
    messages = _start_messages(_token(store["id"], call_sid="CA-other"), call_sid="CA123")

    assert _close_code(user_client, messages) == 1008


def test_store_that_turned_phone_ordering_off_is_refused(user_client, session_factory, store):
    with session_factory() as db:
        db.get(Store, store["id"]).phone_ai_enabled = False
        db.commit()

    assert _close_code(user_client, _start_messages(_token(store["id"]))) == 1008


def test_unknown_event_before_start_is_refused(user_client, store):
    assert _close_code(user_client, [{"event": "media", "media": {"payload": ""}}]) == 1008


def test_valid_stream_starts_a_phone_session(user_client, store, monkeypatch):
    captured = {}

    def fake_handlers(context, **kwargs):
        captured["context"] = context
        return {}

    def fake_task(**kwargs):
        captured["task_kwargs"] = kwargs
        raise RuntimeError("stop before running the real pipeline")

    monkeypatch.setattr(twilio_module, "create_twilio_transport", lambda ws, **kw: captured.update(transport=kw))
    monkeypatch.setattr(twilio_module, "create_voice_tool_handlers", fake_handlers)
    monkeypatch.setattr(twilio_module, "create_voice_pipeline_task", fake_task)

    assert _close_code(user_client, _start_messages(_token(store["id"]))) == 1011

    ctx = captured["context"]
    assert (ctx.store_id, ctx.user_id, ctx.channel, ctx.customer_phone) == (store["id"], None, "phone", CALLER)
    assert captured["transport"] == {"stream_sid": "MZ123"}
    kwargs = captured["task_kwargs"]
    assert "Hot Wok" in kwargs["greeting"] and "## Phone call" in kwargs["system_prompt"]
    assert "already on the order" in kwargs["system_prompt"]  # caller ID came through
    tools = {t["name"] for t in kwargs["tool_schema"][0]["function_declarations"]}
    assert "set_callback_number" in tools
    assert "transfer_to_staff" not in tools  # no staff number to hand calls to


def test_transfer_tool_offered_when_store_has_staff_number(user_client, session_factory, store, monkeypatch):
    with session_factory() as db:
        db.get(Store, store["id"]).phone_staff_number = "+16025559999"
        db.commit()
    captured = {}

    def fake_task(**kwargs):
        captured.update(kwargs)
        raise RuntimeError("stop")

    monkeypatch.setattr(twilio_module, "create_twilio_transport", lambda ws, **kw: None)
    monkeypatch.setattr(twilio_module, "create_voice_pipeline_task", fake_task)

    _close_code(user_client, _start_messages(_token(store["id"])))

    tools = {t["name"] for t in captured["tool_schema"][0]["function_declarations"]}
    assert "transfer_to_staff" in tools
    assert "press 0" in captured["system_prompt"]


def test_phone_order_has_no_account_and_keeps_caller_number(db_factory, session_factory, store):
    ctx = VoiceToolContext(
        db_factory=db_factory, store_id=store["id"], user_id=None, channel="phone", customer_phone=CALLER
    )
    router = VoiceToolRouter(ctx)

    assert router.add_item(menu_item_id=store["item_id"], item_name=None, quantity=2)["ok"]
    assert router.add_item(menu_item_id=store["item_id"], item_name=None, quantity=1)["ok"]

    with session_factory() as db:
        orders = db.query(Order).all()
        assert len(orders) == 1
        order = orders[0]
        assert (order.user_id, order.channel, order.customer_phone) == (None, "phone", CALLER)
        assert order.id == ctx.order_id and isinstance(order.id, uuid.UUID)


def _phone_router(db_factory, store, *, caller=None):
    ctx = VoiceToolContext(
        db_factory=db_factory, store_id=store["id"], user_id=None, channel="phone", customer_phone=caller
    )
    return VoiceToolRouter(ctx)


def test_hidden_caller_must_give_a_callback_number(db_factory, session_factory, store):
    router = _phone_router(db_factory, store)
    assert router.add_item(menu_item_id=store["item_id"], item_name=None, quantity=1)["ok"]
    assert router.set_fulfillment(type="pickup")["ok"]
    assert router.set_customer_name(name="Ann")["ok"]
    ctx = router._context
    ctx.name_set_at -= 5
    ctx.bot_speech_ended_at = ctx.name_set_at + 1

    refused = router.ask_to_place_order()
    assert not refused["ok"] and "set_callback_number" in refused["message"]

    assert not router.set_callback_number(phone="555-1234")["ok"]
    saved = router.set_callback_number(phone="(480) 555-1234")
    assert saved["ok"] and saved["read_back"] == "four eight zero, five five five, one two three four"
    assert router.ask_to_place_order()["ok"]
    with session_factory() as db:
        assert db.get(Order, ctx.order_id).customer_phone == CALLER


def test_transfer_to_staff_flags_the_call(db_factory, store):
    router = _phone_router(db_factory, store, caller=CALLER)

    result = router.transfer_to_staff()

    assert result["ok"] and result["say"] and router._context.transfer_requested
