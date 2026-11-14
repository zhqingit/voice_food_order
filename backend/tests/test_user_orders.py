from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from app.core.security import create_access_token
from app.models.order import Order
from app.models.store import Store
from app.models.user import User
from app.schemas.common import Audience, PrincipalType


@pytest.fixture()
def world(session_factory):
    with session_factory() as db:
        store = Store(name="Hot Wok", email="wok@example.com", password_hash="x", is_published=True, is_approved=True)
        alice = User(email="alice@example.com", password_hash="x")
        bob = User(email="bob@example.com", password_hash="x")
        db.add_all([store, alice, bob])
        db.flush()

        def order(code, status, user=alice, minutes_ago=0, paid=False):
            o = Order(
                store_id=store.id, user_id=user.id, status=status, channel="voice", short_code=code,
                code_day=date(2026, 11, 14), total=Decimal("15.08"),
                payment_status="paid" if paid else "unpaid",
                created_at=datetime(2026, 11, 14, 12) - timedelta(minutes=minutes_ago),
            )
            db.add(o)
            db.flush()
            return o.id

        ids = {
            "draft": order("DRAFT", "draft"),
            "old": order("OLD01", "completed", minutes_ago=60, paid=True),
            "new": order("NEW01", "submitted", minutes_ago=1),
            "cancelled": order("CXL01", "cancelled", minutes_ago=30),
            "bobs": order("BOB01", "submitted", user=bob),
        }
        db.commit()
        token = create_access_token(subject=str(alice.id), role=PrincipalType.user, audience=Audience.mobile)
        return {"ids": ids, "headers": {"Authorization": f"Bearer {token}"}}


def test_my_orders_lists_placed_orders_newest_first(user_client, world):
    r = user_client.get("/user/orders", headers=world["headers"])

    assert r.status_code == 200, r.text
    orders = r.json()
    assert [o["short_code"] for o in orders] == ["NEW01", "CXL01", "OLD01"]  # no draft, no one else's
    assert all(o["store_name"] == "Hot Wok" for o in orders)
    assert {o["short_code"]: o["payment_status"] for o in orders}["OLD01"] == "paid"
    assert not any(o["can_pay_online"] for o in orders)  # the store has no Stripe account


def test_open_unpaid_order_can_be_paid_online_once_store_takes_payments(user_client, world, session_factory):
    with session_factory() as db:
        store = db.query(Store).one()
        store.stripe_account_id, store.stripe_charges_enabled = "acct_123", True
        db.commit()

    orders = user_client.get("/user/orders", headers=world["headers"]).json()

    assert {o["short_code"]: o["can_pay_online"] for o in orders} == {"NEW01": True, "CXL01": False, "OLD01": False}


@pytest.mark.parametrize("key", ["draft", "cancelled", "old"])
def test_only_open_orders_can_be_paid(user_client, world, key):
    order_id = world["ids"][key]

    r = user_client.post(f"/voice/orders/{order_id}/payment-intent", headers=world["headers"])

    expected = "already_paid" if key == "old" else "order_not_payable"
    assert r.status_code == 409 and r.json()["code"] == expected


def test_open_unpaid_order_falls_back_to_pay_at_store(user_client, world):
    # The test store has no Stripe account, so no charge is attempted.
    r = user_client.post(f"/voice/orders/{world['ids']['new']}/payment-intent", headers=world["headers"])

    assert r.status_code == 200, r.text
    assert r.json()["payment_available"] is False
