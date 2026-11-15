import uuid
from decimal import Decimal

import pytest

from app.core.security import create_access_token, hash_password
from app.models.admin import Admin
from app.models.order import Order
from app.models.store import Store
from app.models.user import User
from app.schemas.common import Audience, PrincipalType
from app.schemas.menu.menu import MenuItemCreate
from app.schemas.order.order import OrderCreate, OrderItemCreate
from app.services import menu_service, order_payments, order_service
from tests.test_order_payments import stripe_calls, webhook  # noqa: F401  (shared fixtures)

# Platform defaults: 15% on app orders, 10% on phone orders.


@pytest.fixture()
def store(store_client, session_factory):
    r = store_client.post("/store/auth/signup", json={"email": "wok@example.com", "password": "password123", "name": "Hot Wok"})
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    store_id = uuid.UUID(store_client.get("/store/me", headers=headers).json()["id"])
    with session_factory() as db:
        db.get(Store, store_id).tax_rate = Decimal("0.1000")
        rice = menu_service.create_store_item(db, store_id=store_id, payload=MenuItemCreate(name="Fried Rice", price=Decimal("10.00")))
        db.commit()
        return {"id": store_id, "rice": rice.id, "headers": headers}


def _order(session_factory, store, channel, quantity=1):
    with session_factory() as db:
        order = order_service.create_draft_order(
            db,
            payload=OrderCreate(
                store_id=store["id"], channel=channel, items=[OrderItemCreate(menu_item_id=store["rice"], quantity=quantity)]
            ),
        )
        db.commit()
        return order.id


def _get(session_factory, order_id):
    with session_factory() as db:
        order = db.get(Order, order_id)
        return order.commission_bps, order.commission


def test_commission_depends_on_the_channel_and_is_on_the_pre_tax_subtotal(session_factory, store):
    app_order = _order(session_factory, store, "voice", quantity=2)  # $20 subtotal, $22 with tax
    phone_order = _order(session_factory, store, "phone", quantity=2)

    assert _get(session_factory, app_order) == (1500, Decimal("3.00"))
    assert _get(session_factory, phone_order) == (1000, Decimal("2.00"))


def test_rate_change_only_affects_new_orders(session_factory, store):
    before = _order(session_factory, store, "phone")
    with session_factory() as db:
        db.get(Store, store["id"]).commission_phone_bps = 800
        db.commit()
    after = _order(session_factory, store, "phone")

    assert _get(session_factory, before)[0] == 1000
    assert _get(session_factory, after)[0] == 800


def test_staff_edits_recompute_the_commission_at_the_locked_rate(store_client, session_factory, store):
    order_id = _order(session_factory, store, "voice")
    with session_factory() as db:
        db.get(Order, order_id).status = "confirmed"
        db.get(Store, store["id"]).commission_app_bps = 2000  # changed after the order was placed
        db.commit()

    store_client.post(f"/store/orders/{order_id}/items", json={"menu_item_id": str(store["rice"])}, headers=store["headers"])

    assert _get(session_factory, order_id) == (1500, Decimal("3.00"))


def test_online_payments_take_only_the_commission_not_yet_collected(user_client, store_client, session_factory, store, stripe_calls, webhook, user):
    order_id = _order(session_factory, store, "voice")
    with session_factory() as db:
        order = db.get(Order, order_id)
        order.status, order.user_id = "confirmed", user["id"]
        s = db.get(Store, store["id"])
        s.stripe_account_id, s.stripe_charges_enabled = "acct_1", True
        db.commit()

    def pay():
        r = user_client.post(f"/voice/orders/{order_id}/payment-intent", headers=user["headers"])
        pi = r.json()["client_secret"].removesuffix("_secret")
        webhook("payment_intent.succeeded", {"id": pi, "amount_received": r.json()["amount"], "metadata": {"order_id": str(order_id)}})

    pay()  # $11.00, commission $1.50
    store_client.post(f"/store/orders/{order_id}/items", json={"menu_item_id": str(store["rice"])}, headers=store["headers"])
    pay()  # the $11.00 balance; commission is now $3.00, so $1.50 more

    assert stripe_calls["fees"] == [Decimal("1.50"), Decimal("1.50")]

    store_client.post(f"/store/orders/{order_id}/refunds", json={"amount": "5.50"}, headers=store["headers"])

    with session_factory() as db:
        # Half of the second charge went back, and with it half of its fee.
        assert order_payments.ledger(db, db.get(Order, order_id)).commission_collected == Decimal("2.25")


def test_admin_sets_rates_per_channel_and_a_monthly_fee(admin_client, admin_headers, store):
    r = admin_client.patch(
        f"/admin/stores/{store['id']}",
        json={"commission_phone_bps": 800, "monthly_fee": "49.00"},
        headers=admin_headers,
    )

    body = r.json()
    assert r.status_code == 200, r.text
    assert (body["effective_app_bps"], body["effective_phone_bps"], body["monthly_fee"]) == (1500, 800, "49.00")

    r = admin_client.patch(f"/admin/stores/{store['id']}", json={"commission_phone_bps": None}, headers=admin_headers)

    assert r.json()["effective_phone_bps"] == 1000  # back to the platform default


def test_the_store_sees_its_rates_and_monthly_fee(admin_client, admin_headers, store_client, store):
    admin_client.patch(f"/admin/stores/{store['id']}", json={"monthly_fee": "49.00"}, headers=admin_headers)

    r = store_client.get("/store/payments/status", headers=store["headers"])

    assert (r.json()["fee_app_bps"], r.json()["fee_phone_bps"], r.json()["monthly_fee"]) == (1500, 1000, "49.00")


@pytest.fixture()
def admin_headers(session_factory):
    with session_factory() as db:
        admin = Admin(email="admin@example.com", password_hash=hash_password("password123"))
        db.add(admin)
        db.commit()
        token = create_access_token(subject=str(admin.id), role=PrincipalType.admin, audience=Audience.admin)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def user(session_factory):
    with session_factory() as db:
        u = User(email="alice@example.com", password_hash="x")
        db.add(u)
        db.commit()
        token = create_access_token(subject=str(u.id), role=PrincipalType.user, audience=Audience.mobile)
        return {"id": u.id, "headers": {"Authorization": f"Bearer {token}"}}
