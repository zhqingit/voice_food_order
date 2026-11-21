import uuid

import pytest

from app.core.security import create_access_token
from app.models.store import Store
from app.models.user import User
from app.schemas.common import Audience, PrincipalType

COMPLETE = {
    "address_line1": "910 N Alma School Rd", "city": "Chandler", "state": "AZ",
    "postal_code": "85224", "country": "US", "tax_rate": "0",
}


@pytest.fixture()
def store(store_client):
    r = store_client.post("/store/auth/signup", json={"email": "wok@example.com", "password": "password123", "name": "Hot Wok"})
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    return {"id": store_client.get("/store/me", headers=headers).json()["id"], "headers": headers}


def test_a_new_store_must_complete_its_profile_before_publishing(store_client, store):
    me = store_client.get("/store/me", headers=store["headers"]).json()
    assert me["tax_rate"] is None  # empty until entered

    r = store_client.patch("/store/me", json={"is_published": True}, headers=store["headers"])
    assert r.status_code == 422 and r.json()["code"] == "profile_incomplete"
    assert r.json()["detail"] == "Missing: address_line1, city, state, postal_code, country, tax_rate"

    r = store_client.patch("/store/me", json={**COMPLETE, "is_published": True}, headers=store["headers"])
    assert r.status_code == 200 and r.json()["is_published"] is True and r.json()["tax_rate"] == "0.0000"  # 0 is fine

    r = store_client.patch("/store/me", json={"city": " "}, headers=store["headers"])
    assert r.status_code == 422 and r.json()["code"] == "profile_incomplete"  # can't clear it while published


def test_the_app_cannot_start_a_voice_order_while_the_store_is_closed(store_client, user_client, session_factory, store):
    with session_factory() as db:
        s = db.get(Store, uuid.UUID(store["id"]))
        s.is_published = s.is_approved = True
        user = User(email="alice@example.com", password_hash="x")
        db.add(user)
        db.commit()
        token = create_access_token(subject=str(user.id), role=PrincipalType.user, audience=Audience.mobile)
    closed_all_week = [{"day_of_week": d, "open_time": "11:00", "close_time": "21:00", "is_closed": True} for d in range(7)]
    store_client.put("/store/me/hours", json={"hours": closed_all_week}, headers=store["headers"])

    r = user_client.post(
        "/voice/sessions", json={"store_id": store["id"], "channel": "voice"}, headers={"Authorization": f"Bearer {token}"}
    )

    assert r.status_code == 409 and r.json()["code"] == "store_closed"


def test_stores_cannot_read_ai_usage(store_client, store):
    r = store_client.get(f"/store/orders/{uuid.uuid4()}/usage", headers=store["headers"])

    assert r.status_code in (404, 405)


def test_the_app_is_told_whether_the_store_is_open_now(store_client, user_client, session_factory, store):
    with session_factory() as db:
        s = db.get(Store, uuid.UUID(store["id"]))
        s.is_published = s.is_approved = True
        db.commit()
    assert user_client.get(f"/user/stores/{store['id']}").json()["is_open_now"] is None  # no hours: always open

    closed_all_week = [{"day_of_week": d, "open_time": "11:00", "close_time": "21:00", "is_closed": True} for d in range(7)]
    store_client.put("/store/me/hours", json={"hours": closed_all_week}, headers=store["headers"])

    assert user_client.get(f"/user/stores/{store['id']}").json()["is_open_now"] is False


def test_the_app_is_not_sent_ai_usage_or_cost(user_client, session_factory, store):
    with session_factory() as db:
        s = db.get(Store, uuid.UUID(store["id"]))
        s.is_published = s.is_approved = True
        user = User(email="bob@example.com", password_hash="x")
        db.add(user)
        db.commit()
        headers = {"Authorization": f"Bearer {create_access_token(subject=str(user.id), role=PrincipalType.user, audience=Audience.mobile)}"}

    created = user_client.post("/voice/sessions", json={"store_id": store["id"], "channel": "voice"}, headers=headers)
    ended = user_client.post(f"/voice/sessions/{created.json()['id']}/end", headers=headers)

    for body in (created.json(), ended.json()):
        assert not {"llm_cost", "prompt_tokens", "completion_tokens", "total_tokens"} & body.keys()
