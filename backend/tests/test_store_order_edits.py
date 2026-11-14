import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.core.security import create_access_token
from app.models.menu_item_variant import MenuItemVariant
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.store import Store
from app.models.user import User
from app.schemas.common import Audience, PrincipalType
from app.schemas.menu.menu import MenuItemCreate
from app.services import menu_service


@pytest.fixture()
def world(store_client, session_factory):
    r = store_client.post("/store/auth/signup", json={"email": "wok@example.com", "password": "password123", "name": "Hot Wok"})
    assert r.status_code == 200, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    store_id = uuid.UUID(store_client.get("/store/me", headers=headers).json()["id"])

    with session_factory() as db:
        store = db.get(Store, store_id)
        store.tax_rate, store.phone = Decimal("0.1000"), "+14805550000"
        rice = menu_service.create_store_item(db, store_id=store_id, payload=MenuItemCreate(name="Fried Rice", price=Decimal("10.00")))
        beef = menu_service.create_store_item(
            db,
            store_id=store_id,
            payload=MenuItemCreate(name="Beijing Beef", price=Decimal("12.00"), price_small=Decimal("9.00"), price_large=Decimal("14.00")),
        )
        user = User(email="alice@example.com", password_hash="x")
        db.add(user)
        db.flush()
        order = Order(
            store_id=store_id, user_id=user.id, status="confirmed", channel="voice", short_code="ABC12",
            code_day=date(2026, 11, 14), subtotal=Decimal("10.00"), tax=Decimal("1.00"), total=Decimal("11.00"),
        )
        db.add(order)
        db.flush()
        line = OrderItem(order_id=order.id, menu_item_id=rice.id, quantity=1, price_snapshot=Decimal("10.00"))
        db.add(line)
        db.commit()
        large = db.query(MenuItemVariant).filter_by(menu_item_id=beef.id).filter(MenuItemVariant.price == Decimal("14.00")).one()
        token = create_access_token(subject=str(user.id), role=PrincipalType.user, audience=Audience.mobile)
        return {
            "headers": headers,
            "order": order.id,
            "line": line.id,
            "rice": rice.id,
            "beef": beef.id,
            "large": large.id,
            "user_headers": {"Authorization": f"Bearer {token}"},
        }


def _url(world, suffix=""):
    return f"/store/orders/{world['order']}{suffix}"


def test_staff_add_change_and_remove_items_with_totals_and_history(store_client, world):
    h = world["headers"]

    r = store_client.post(_url(world, "/items"), json={"menu_item_id": str(world["beef"]), "variant_id": str(world["large"]), "quantity": 2}, headers=h)
    assert r.status_code == 200, r.text
    assert (r.json()["subtotal"], r.json()["total"]) == ("38.00", "41.80")  # 10 + 2×14, plus 10% tax

    r = store_client.patch(_url(world, f"/items/{world['line']}"), json={"quantity": 3, "note": "extra egg"}, headers=h)
    assert r.json()["subtotal"] == "58.00"

    r = store_client.delete(_url(world, f"/items/{world['line']}"), headers=h)
    assert r.json()["subtotal"] == "28.00"

    events = store_client.get(_url(world, "/events"), headers=h).json()
    assert [e["kind"] for e in events] == ["item_added", "item_updated", "item_removed"]
    assert events[0]["detail"] == "2 × Beijing Beef (Large)" and events[0]["total_before"] == "11.00"
    assert events[1]["detail"] == 'Fried Rice: ×1 → ×3, note: "extra egg"'
    assert events[2]["total_after"] == "30.80"


def test_item_with_options_needs_one(store_client, world):
    r = store_client.post(_url(world, "/items"), json={"menu_item_id": str(world["beef"])}, headers=world["headers"])

    assert r.status_code == 422 and r.json()["code"] == "variant_required"


def test_last_item_cannot_be_removed(store_client, world):
    r = store_client.delete(_url(world, f"/items/{world['line']}"), headers=world["headers"])

    assert r.status_code == 409 and r.json()["code"] == "last_item"


def test_cancelled_order_is_locked_and_cancel_is_logged(store_client, world):
    h = world["headers"]
    assert store_client.patch(_url(world), json={"status": "cancelled"}, headers=h).status_code == 200

    r = store_client.post(_url(world, "/items"), json={"menu_item_id": str(world["rice"])}, headers=h)

    assert r.status_code == 409 and r.json()["code"] == "order_not_editable"
    events = store_client.get(_url(world, "/events"), headers=h).json()
    assert [(e["kind"], e["detail"]) for e in events] == [("status_changed", "confirmed → cancelled")]


def test_customer_sees_store_phone_and_that_the_store_changed_the_order(store_client, user_client, world):
    def my_order():
        return user_client.get("/user/orders", headers=world["user_headers"]).json()[0]

    assert my_order()["store_phone"] == "+14805550000" and my_order()["modified_by_store"] is False

    store_client.post(_url(world, "/items"), json={"menu_item_id": str(world["rice"])}, headers=world["headers"])

    assert my_order()["modified_by_store"] is True


def test_other_stores_orders_are_not_editable(store_client, world):
    r = store_client.post("/store/auth/signup", json={"email": "other@example.com", "password": "password123", "name": "Other"})
    other = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = store_client.post(_url(world, "/items"), json={"menu_item_id": str(world["rice"])}, headers=other)

    assert r.status_code == 404
