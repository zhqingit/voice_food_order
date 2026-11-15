import itertools
import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.core.security import create_access_token
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.store import Store
from app.models.user import User
from app.schemas.common import Audience, PrincipalType
from app.schemas.menu.menu import MenuItemCreate
from app.services import menu_service, payment_service


@pytest.fixture()
def stripe_calls(monkeypatch):
    """Fake Stripe: every call is recorded, nothing leaves the machine."""
    calls = {"intents": [], "fees": [], "cancelled": [], "refunds": []}
    ids = itertools.count(1)

    def create_payment_intent(order, store, *, amount_due, application_fee):
        pi = f"pi_{next(ids)}"
        calls["intents"].append((pi, amount_due))
        calls["fees"].append(application_fee)
        return payment_service.PaymentIntentResult(client_secret=f"{pi}_secret", payment_intent_id=pi)

    def retrieve_payment_intent(pi):
        return payment_service.PaymentIntentState(status="requires_payment_method", client_secret=f"{pi}_secret", amount=0)

    def cancel_payment_intent(pi):
        calls["cancelled"].append(pi)
        return True

    def create_refund(pi, *, amount, order_id):
        re = f"re_{next(ids)}"
        calls["refunds"].append((pi, amount))
        return payment_service.RefundResult(refund_id=re, status="succeeded")

    monkeypatch.setattr(payment_service, "create_payment_intent", create_payment_intent)
    monkeypatch.setattr(payment_service, "retrieve_payment_intent", retrieve_payment_intent)
    monkeypatch.setattr(payment_service, "cancel_payment_intent", cancel_payment_intent)
    monkeypatch.setattr(payment_service, "create_refund", create_refund)
    return calls


@pytest.fixture()
def world(store_client, session_factory, stripe_calls):
    r = store_client.post("/store/auth/signup", json={"email": "wok@example.com", "password": "password123", "name": "Hot Wok"})
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    store_id = uuid.UUID(store_client.get("/store/me", headers=headers).json()["id"])

    with session_factory() as db:
        store = db.get(Store, store_id)
        store.tax_rate, store.phone = Decimal("0.1000"), "+14805550000"
        store.stripe_account_id, store.stripe_charges_enabled = "acct_1", True
        rice = menu_service.create_store_item(db, store_id=store_id, payload=MenuItemCreate(name="Fried Rice", price=Decimal("10.00")))
        user = User(email="alice@example.com", password_hash="x")
        db.add(user)
        db.flush()
        order = Order(
            store_id=store_id, user_id=user.id, status="submitted", channel="voice", short_code="ABC12",
            code_day=date(2026, 11, 14), subtotal=Decimal("10.00"), tax=Decimal("1.00"), total=Decimal("11.00"),
            commission_bps=1500, commission=Decimal("1.50"),  # 15% of the pre-tax subtotal
        )
        db.add(order)
        db.flush()
        line = OrderItem(order_id=order.id, menu_item_id=rice.id, quantity=1, price_snapshot=Decimal("10.00"))
        db.add(line)
        db.commit()
        token = create_access_token(subject=str(user.id), role=PrincipalType.user, audience=Audience.mobile)
        return {
            "store": headers,
            "user": {"Authorization": f"Bearer {token}"},
            "order": order.id,
            "line": line.id,
            "rice": rice.id,
        }


@pytest.fixture()
def webhook(store_client, monkeypatch):
    def send(event_type, obj):
        monkeypatch.setattr(payment_service, "verify_webhook", lambda payload, sig: {"type": event_type, "data": {"object": obj}})
        r = store_client.post("/webhooks/stripe", content=b"{}", headers={"stripe-signature": "t=1,v1=x"})
        assert r.status_code == 200, r.text

    return send


def _pay(user_client, world, webhook):
    """Customer opens the payment sheet and Stripe reports the payment."""
    r = user_client.post(f"/voice/orders/{world['order']}/payment-intent", headers=world["user"])
    assert r.status_code == 200, r.text
    pi = r.json()["client_secret"].removesuffix("_secret")
    webhook("payment_intent.succeeded", {"id": pi, "amount_received": r.json()["amount"], "metadata": {"order_id": str(world["order"])}})
    return r.json()["amount"]


def _my_order(user_client, world):
    return user_client.get("/user/orders", headers=world["user"]).json()[0]


def _payments(store_client, world):
    return store_client.get(f"/store/orders/{world['order']}/payments", headers=world["store"]).json()


def _events(store_client, world):
    return [e["kind"] for e in store_client.get(f"/store/orders/{world['order']}/events", headers=world["store"]).json()]


def test_reopening_the_payment_sheet_reuses_the_unfinished_charge(user_client, world, stripe_calls):
    url = f"/voice/orders/{world['order']}/payment-intent"
    first = user_client.post(url, headers=world["user"]).json()
    second = user_client.post(url, headers=world["user"]).json()

    assert first["client_secret"] == second["client_secret"]
    assert len(stripe_calls["intents"]) == 1


def test_paid_order_raised_by_staff_owes_only_the_difference(store_client, user_client, world, webhook, stripe_calls):
    assert _pay(user_client, world, webhook) == 1100
    assert _my_order(user_client, world)["payment_status"] == "paid"

    store_client.patch(f"/store/orders/{world['order']}/items/{world['line']}", json={"quantity": 2}, headers=world["store"])

    mine = _my_order(user_client, world)
    assert (mine["payment_status"], mine["amount_paid"], mine["balance_due"], mine["can_pay_online"]) == (
        "partially_paid", "11.00", "11.00", True,
    )
    assert _pay(user_client, world, webhook) == 1100  # only the balance
    assert _my_order(user_client, world)["payment_status"] == "paid"
    assert [amount for _, amount in stripe_calls["intents"]] == [Decimal("11.00"), Decimal("11.00")]


def test_staff_refund_the_overpayment_after_lowering_the_total(store_client, user_client, world, webhook, stripe_calls):
    store_client.patch(f"/store/orders/{world['order']}/items/{world['line']}", json={"quantity": 2}, headers=world["store"])
    _pay(user_client, world, webhook)  # $22.00
    store_client.patch(f"/store/orders/{world['order']}/items/{world['line']}", json={"quantity": 1}, headers=world["store"])
    assert _payments(store_client, world)["overpaid"] == "11.00"

    too_much = store_client.post(f"/store/orders/{world['order']}/refunds", json={"amount": "30.00"}, headers=world["store"])
    assert too_much.status_code == 422 and too_much.json()["code"] == "refund_exceeds_paid"

    r = store_client.post(f"/store/orders/{world['order']}/refunds", json={"amount": "11.00"}, headers=world["store"])
    assert r.status_code == 200, r.text
    assert (r.json()["net"], r.json()["overpaid"]) == ("11.00", "0.00")
    assert stripe_calls["refunds"] == [("pi_1", Decimal("11.00"))]
    assert _my_order(user_client, world)["payment_status"] == "paid"
    assert "refund_issued" in _events(store_client, world)


def test_customer_cancels_before_the_store_accepts_and_gets_the_money_back(user_client, world, webhook, stripe_calls):
    _pay(user_client, world, webhook)

    r = user_client.post(f"/user/orders/{world['order']}/cancel", headers=world["user"])

    assert r.status_code == 200, r.text
    assert (r.json()["status"], r.json()["payment_status"], r.json()["amount_paid"]) == ("cancelled", "refunded", "0.00")
    assert stripe_calls["refunds"] == [("pi_1", Decimal("11.00"))]


def test_customer_cannot_cancel_after_the_store_accepts(store_client, user_client, world):
    store_client.patch(f"/store/orders/{world['order']}", json={"status": "confirmed"}, headers=world["store"])

    r = user_client.post(f"/user/orders/{world['order']}/cancel", headers=world["user"])

    assert r.status_code == 409 and r.json()["code"] == "order_not_cancellable"


def test_cancelling_stops_an_unfinished_payment_and_refunds_one_that_lands_anyway(user_client, world, webhook, stripe_calls):
    user_client.post(f"/voice/orders/{world['order']}/payment-intent", headers=world["user"])
    user_client.post(f"/user/orders/{world['order']}/cancel", headers=world["user"])
    assert stripe_calls["cancelled"] == ["pi_1"]

    # Stripe had already taken the money: it goes straight back.
    webhook("payment_intent.succeeded", {"id": "pi_1", "amount_received": 1100, "metadata": {"order_id": str(world["order"])}})

    assert stripe_calls["refunds"] == [("pi_1", Decimal("11.00"))]
    assert _my_order(user_client, world)["payment_status"] == "refunded"


def test_staff_record_the_balance_taken_at_the_counter(store_client, user_client, world):
    url = f"/store/orders/{world['order']}/payments"
    too_much = store_client.post(url, json={"amount": "20.00"}, headers=world["store"])
    assert too_much.status_code == 422 and too_much.json()["code"] == "amount_exceeds_balance"

    r = store_client.post(url, json={"amount": "11.00"}, headers=world["store"])

    assert r.status_code == 200 and r.json()["balance_due"] == "0.00"
    assert _my_order(user_client, world)["payment_status"] == "paid"


def test_failed_refund_is_logged_and_the_money_counts_as_paid_again(store_client, user_client, world, webhook):
    _pay(user_client, world, webhook)
    store_client.patch(f"/store/orders/{world['order']}", json={"status": "cancelled"}, headers=world["store"])
    store_client.post(f"/store/orders/{world['order']}/refunds", json={"amount": "11.00"}, headers=world["store"])
    assert _payments(store_client, world)["net"] == "0.00"

    # The fake Stripe numbers refunds after the PaymentIntent: pi_1 → re_2.
    webhook("refund.failed", {"id": "re_2", "payment_intent": "pi_1", "amount": 1100, "status": "failed"})

    assert _payments(store_client, world)["net"] == "11.00"
    assert "refund_failed" in _events(store_client, world)


def test_refund_made_in_the_stripe_dashboard_is_picked_up(store_client, user_client, world, webhook):
    _pay(user_client, world, webhook)

    webhook("refund.created", {"id": "re_dash", "payment_intent": "pi_1", "amount": 500, "status": "succeeded"})

    assert _payments(store_client, world)["net"] == "6.00"
    assert _my_order(user_client, world)["payment_status"] == "partially_paid"


def test_lost_dispute_takes_the_money_back(store_client, user_client, world, webhook):
    _pay(user_client, world, webhook)

    webhook("charge.dispute.created", {"id": "du_1", "payment_intent": "pi_1", "amount": 1100, "status": "needs_response", "reason": "fraudulent"})
    webhook("charge.dispute.closed", {"id": "du_1", "payment_intent": "pi_1", "amount": 1100, "status": "lost"})

    assert _my_order(user_client, world)["payment_status"] == "refunded"
    assert {"dispute_opened", "dispute_closed"} <= set(_events(store_client, world))


def test_notice_for_the_customer_lists_changes_until_they_are_told(store_client, user_client, world, webhook):
    url = f"/store/orders/{world['order']}/customer-notice"
    _pay(user_client, world, webhook)
    assert store_client.get(url, headers=world["store"]).json()["pending"] is False

    store_client.post(f"/store/orders/{world['order']}/items", json={"menu_item_id": str(world["rice"])}, headers=world["store"])

    notice = store_client.get(url, headers=world["store"]).json()
    assert notice["pending"] is True and notice["sms_available"] is False
    assert notice["message"] == (
        "Hot Wok: your order #ABC12 was updated: added 1 × Fried Rice. New total $22.00. "
        "Balance due: $11.00, payable in the VoxEats app or at pickup. Questions? Call +14805550000."
    )
    sms = store_client.post(url, json={"method": "sms"}, headers=world["store"])
    assert sms.status_code == 409 and sms.json()["code"] == "sms_not_available"

    r = store_client.post(url, json={"method": "call"}, headers=world["store"])

    assert r.status_code == 200 and r.json()["pending"] is False
    assert "customer_notified" in _events(store_client, world)
