import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.store import Store
from app.schemas.menu.menu import MenuItemCreate
from app.schemas.order.order import OrderCreate, OrderItemCreate
from app.services import menu_service, order_service
from app.voice.prompts import build_system_prompt
from app.voice.session_setup import load_store_voice_setup
from app.voice.tool_router import VoiceToolContext, VoiceToolRouter


@pytest.fixture()
def wok(store_client, session_factory):
    r = store_client.post("/store/auth/signup", json={"email": "wok@example.com", "password": "password123", "name": "Hot Wok"})
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    store_id = uuid.UUID(store_client.get("/store/me", headers=headers).json()["id"])
    with session_factory() as db:
        store = db.get(Store, store_id)
        store.tax_rate = Decimal("0.1000")
        store.is_published = store.is_approved = True
        rice = menu_service.create_store_item(db, store_id=store_id, payload=MenuItemCreate(name="Fried Rice", price=Decimal("10.00")))
        db.commit()
        return {"id": store_id, "rice": rice.id, "headers": headers}


def _promo(store_client, wok, **terms):
    body = {"name": "Deal", "kind": "percent", "value": "10", **terms}
    r = store_client.post("/store/promotions", json=body, headers=wok["headers"])
    assert r.status_code == 201, r.text
    return r.json()


def _draft(session_factory, wok, quantity, channel="voice"):
    with session_factory() as db:
        order = order_service.create_draft_order(
            db, payload=OrderCreate(store_id=wok["id"], channel=channel, items=[OrderItemCreate(menu_item_id=wok["rice"], quantity=quantity)])
        )
        db.commit()
        return order.id


def _money(session_factory, order_id):
    with session_factory() as db:
        o = db.get(Order, order_id)
        return o.subtotal, o.discount, o.tax, o.total, o.commission


def test_discount_comes_off_before_tax_and_commission(store_client, session_factory, wok):
    _promo(store_client, wok, name="Grand opening", value="10")

    order_id = _draft(session_factory, wok, 2)  # $20.00

    # 10% off → $18.00; tax 10% → $1.80; commission 15% of $18.00 → $2.70
    assert _money(session_factory, order_id) == (
        Decimal("20.00"), Decimal("2.00"), Decimal("1.80"), Decimal("19.80"), Decimal("2.70"),
    )


def test_the_best_promotion_wins_and_store_promotions_do_not_stack(store_client, session_factory, wok):
    _promo(store_client, wok, name="10% off", value="10")
    _promo(store_client, wok, name="$5 off $30", kind="amount_off", value="5", min_subtotal="30")

    assert _money(session_factory, _draft(session_factory, wok, 2))[1] == Decimal("2.00")  # $20: 10% beats nothing
    assert _money(session_factory, _draft(session_factory, wok, 4))[1] == Decimal("5.00")  # $40: $5 beats $4
    assert _money(session_factory, _draft(session_factory, wok, 6))[1] == Decimal("6.00")  # $60: $6 beats $5


def test_channel_dates_and_switch_decide_whether_a_promotion_runs(store_client, session_factory, wok):
    today = date.today()
    _promo(store_client, wok, name="Phone only", channels="phone")
    _promo(store_client, wok, name="Ended", ends_on=str(today - timedelta(days=2)))
    _promo(store_client, wok, name="Not yet", starts_on=str(today + timedelta(days=2)))
    off = _promo(store_client, wok, name="Paused")
    store_client.patch(f"/store/promotions/{off['id']}", json={"is_active": False}, headers=wok["headers"])

    assert _money(session_factory, _draft(session_factory, wok, 2))[1] == Decimal("0.00")
    assert _money(session_factory, _draft(session_factory, wok, 2, channel="phone"))[1] == Decimal("2.00")


def test_a_placed_order_keeps_its_promotion_through_staff_edits(store_client, session_factory, wok):
    promo = _promo(store_client, wok, name="$5 off $30", kind="amount_off", value="5", min_subtotal="30")
    order_id = _draft(session_factory, wok, 3)
    with session_factory() as db:
        db.get(Order, order_id).status = "confirmed"
        db.commit()
    store_client.patch(f"/store/promotions/{promo['id']}", json={"is_active": False}, headers=wok["headers"])
    _promo(store_client, wok, name="Better deal", value="50")  # created after the order was placed

    store_client.post(f"/store/orders/{order_id}/items", json={"menu_item_id": str(wok["rice"])}, headers=wok["headers"])
    assert _money(session_factory, order_id)[:2] == (Decimal("40.00"), Decimal("5.00"))

    with session_factory() as db:
        three = db.execute(select(OrderItem).where(OrderItem.order_id == order_id, OrderItem.quantity == 3)).scalar_one()
    store_client.patch(f"/store/orders/{order_id}/items/{three.id}", json={"quantity": 1}, headers=wok["headers"])
    assert _money(session_factory, order_id)[:2] == (Decimal("20.00"), Decimal("0.00"))  # under the minimum now


def test_used_promotions_can_be_turned_off_but_not_deleted_or_changed(store_client, session_factory, wok):
    used = _promo(store_client, wok)
    _draft(session_factory, wok, 1)
    unused = _promo(store_client, wok, name="Spare", min_subtotal="500")

    r = store_client.delete(f"/store/promotions/{used['id']}", headers=wok["headers"])
    assert r.status_code == 409 and r.json()["code"] == "promotion_in_use"
    assert store_client.delete(f"/store/promotions/{unused['id']}", headers=wok["headers"]).status_code == 204

    r = store_client.patch(f"/store/promotions/{used['id']}", json={"value": "90"}, headers=wok["headers"])
    assert r.status_code == 200 and r.json()["value"] == "10.00"  # the terms are fixed
    too_much = store_client.post("/store/promotions", json={"name": "x", "kind": "percent", "value": "120"}, headers=wok["headers"])
    assert too_much.status_code == 422


def test_voice_summary_gives_the_assistant_the_discount_and_the_next_deal(store_client, session_factory, db_factory, wok):
    _promo(store_client, wok, name="10% off", value="10")
    _promo(store_client, wok, name="$5 off $30", kind="amount_off", value="5", min_subtotal="30")
    router = VoiceToolRouter(VoiceToolContext(db_factory=db_factory, store_id=wok["id"], user_id=None))

    order = router.add_item(menu_item_id=wok["rice"], item_name=None, quantity=2)["order"]

    assert (order["subtotal"], order["discount"], order["promotion"], order["total"]) == (20.0, 2.0, "10% off", 19.8)
    assert order["next_promotion"]["say"] == "If you add $10.00 more, you'd get $5 off $30 ($5.00 off)."

    order = router.add_item(menu_item_id=wok["rice"], item_name=None, quantity=1)["order"]

    assert (order["discount"], order["promotion"], order["total"]) == (5.0, "$5 off $30", 27.5)
    assert "next_promotion" not in order


def test_the_assistant_is_told_the_running_promotions_and_never_to_do_the_maths(store_client, session_factory, wok):
    _promo(store_client, wok, name="Lunch deal", kind="amount_off", value="3", min_subtotal="20", channels="app")
    _promo(store_client, wok, name="Call-in special", channels="phone")

    with session_factory() as db:
        prompt = load_store_voice_setup(db, db.get(Store, wok["id"])).system_prompt

    assert "- Lunch deal: $3.00 off orders of $20.00 or more (app orders only)" in prompt
    assert "Call-in special" not in prompt  # app session
    assert "NEVER calculate a discount" in prompt
    assert "## Promotions" not in build_system_prompt(store_name="x")


def test_customers_see_the_stores_running_promotions(user_client, store_client, wok):
    _promo(store_client, wok, name="Grand opening", value="15")

    r = user_client.get(f"/user/stores/{wok['id']}")

    assert [(p["name"], p["kind"], p["value"]) for p in r.json()["promotions"]] == [("Grand opening", "percent", "15.00")]
