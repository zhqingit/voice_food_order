import xml.etree.ElementTree as ET
from datetime import time

import pytest

from app.core.config import settings
from app.core.security import hash_password
from app.core.twilio import compute_twilio_signature, create_stream_token, decode_stream_token
from app.models.store import Store
from app.models.store_hours import StoreHours

BASE = "https://voxeats.example.com"
AUTH_TOKEN = "twilio-test-auth-token"
ACCOUNT_SID = "AC" + "0" * 32
AI_NUMBER = "+16232943370"
CALLER = "+14805551234"


@pytest.fixture(autouse=True)
def twilio_settings(monkeypatch):
    monkeypatch.setattr(settings, "public_base_url", BASE + "/")
    monkeypatch.setattr(settings, "telephony_twilio_auth_token", AUTH_TOKEN)
    monkeypatch.setattr(settings, "telephony_twilio_account_sid", ACCOUNT_SID)


def _make_store(session_factory, **overrides):
    fields = dict(
        name="Hot Wok",
        email="wok@example.com",
        password_hash=hash_password("password123"),
        is_approved=True,
        is_published=True,
        phone_ai_number=AI_NUMBER,
        phone_ai_enabled=True,
    )
    fields.update(overrides)
    with session_factory() as db:
        store = Store(**fields)
        db.add(store)
        db.commit()
        return store.id


def _call(client, *, to=AI_NUMBER, sign_with=AUTH_TOKEN, **extra):
    params = {"AccountSid": ACCOUNT_SID, "CallSid": "CA123", "From": CALLER, "To": to, **extra}
    url = BASE + "/voice/telephony/twilio/incoming"
    sig = compute_twilio_signature(url, params, sign_with)
    return client.post("/voice/telephony/twilio/incoming", data=params, headers={"X-Twilio-Signature": sig})


def _twiml(r):
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/xml")
    return ET.fromstring(r.text)


def test_signature_matches_twilio_reference_example():
    # Twilio's docs example; expected value cross-checked with twilio.request_validator.
    params = {
        "CallSid": "CA1234567890ABCDE",
        "Caller": "+12349013030",
        "Digits": "1234",
        "From": "+12349013030",
        "To": "+18005551212",
    }
    url = "https://mycompany.com/myapp.php?foo=1&bar=2"
    assert compute_twilio_signature(url, params, "12345") == "0/KCTR6DLpKmkAf8muzZqo1nDgQ="


def test_enabled_store_streams_call_with_token(user_client, session_factory):
    store_id = _make_store(session_factory)

    root = _twiml(_call(user_client))

    stream = root.find("Connect/Stream")
    assert stream.get("url") == "wss://voxeats.example.com/voice/telephony/twilio/ws"
    token = stream.find("Parameter[@name='token']").get("value")
    grant = decode_stream_token(token)
    assert (grant.store_id, grant.call_sid, grant.caller) == (store_id, "CA123", CALLER)


def test_bad_signature_is_rejected(user_client, session_factory):
    _make_store(session_factory)

    r = _call(user_client, sign_with="wrong-token")

    assert r.status_code == 403 and r.json()["code"] == "invalid_signature"


def test_other_twilio_account_is_rejected(user_client, session_factory, monkeypatch):
    _make_store(session_factory)
    monkeypatch.setattr(settings, "telephony_twilio_account_sid", "AC" + "1" * 32)

    r = _call(user_client)

    assert r.status_code == 403 and r.json()["code"] == "invalid_account"


def test_endpoint_is_off_without_twilio_config(user_client, monkeypatch):
    monkeypatch.setattr(settings, "telephony_twilio_auth_token", None)

    assert _call(user_client).status_code == 404


def test_unknown_number_is_not_in_service(user_client, session_factory):
    _make_store(session_factory)

    root = _twiml(_call(user_client, to="+16025550000"))

    assert "not in service" in root.find("Say").text
    assert root.find("Hangup") is not None


def test_disabled_store_forwards_to_staff_with_caller_id(user_client, session_factory):
    _make_store(session_factory, phone_ai_enabled=False, phone_staff_number="+16025559999")

    root = _twiml(_call(user_client))

    dial = root.find("Dial")
    assert dial.text == "+16025559999" and dial.get("callerId") == CALLER
    assert root.find("Connect") is None


def test_unpublished_store_without_staff_number_apologises(user_client, session_factory):
    _make_store(session_factory, is_published=False)

    root = _twiml(_call(user_client))

    assert "Hot Wok" in root.find("Say").text
    assert root.find("Connect") is None and root.find("Hangup") is not None


def test_anonymous_caller_still_reaches_agent(user_client, session_factory):
    _make_store(session_factory)

    root = _twiml(_call(user_client, From="anonymous"))

    token = root.find("Connect/Stream/Parameter").get("value")
    assert decode_stream_token(token).caller is None


def test_stream_token_is_not_an_access_token():
    import uuid

    from app.core.security import decode_access_token

    token = create_stream_token(store_id=uuid.uuid4(), call_sid="CA1", caller=None)
    with pytest.raises(ValueError):
        decode_access_token(token)
    with pytest.raises(ValueError):
        decode_stream_token(token + "x")


def test_after_the_agent_the_call_falls_through_to_staff(user_client, session_factory):
    _make_store(session_factory, phone_staff_number="+16025559999")

    root = _twiml(_call(user_client))

    # Verbs after <Connect> run once we close the stream (transfer / time limit).
    assert [child.tag for child in root] == ["Connect", "Dial"]
    assert root.find("Dial").text == "+16025559999"


def test_without_staff_the_call_ends_politely_after_the_agent(user_client, session_factory):
    _make_store(session_factory)

    root = _twiml(_call(user_client))

    assert [child.tag for child in root] == ["Connect", "Say", "Hangup"]


def test_closed_store_reads_todays_hours_and_hangs_up(user_client, session_factory):
    store_id = _make_store(session_factory)
    with session_factory() as db:
        for day in range(7):
            db.add(StoreHours(store_id=store_id, day_of_week=day, open_time=time(9), close_time=time(17), is_closed=True))
        db.commit()

    root = _twiml(_call(user_client))

    assert root.find("Connect") is None
    assert "closed right now" in root.find("Say").text and "closed today" in root.find("Say").text
    assert root.find("Hangup") is not None
