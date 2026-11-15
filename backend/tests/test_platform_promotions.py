from datetime import date
from decimal import Decimal

import pytest

from app.models.order import Order
from app.models.store import Store
from app.services import invoice_service, platform_promotions
from app.voice.session_setup import load_store_voice_setup
from app.voice.tool_router import VoiceToolContext, VoiceToolRouter
from tests.test_commission import admin_headers  # noqa: F401  (shared fixture)
from tests.test_order_payments import _pay, stripe_calls, webhook, world  # noqa: F401  (shared fixtures)

# The world order: $10.00 subtotal, $1.00 tax, $11.00 total, 15% commission = $1.50.


@pytest.fixture()
def promo(admin_client, admin_headers):
    def create(**terms):
        body = {"name": "VoxEats deal", "kind": "percent", "value": "10", **terms}
        r = admin_client.post("/admin/promotions", json=body, headers=admin_headers)
        assert r.status_code == 201, r.text
        return r.json()

    return create


def _order(session_factory, world):
    with session_factory() as db:
        o = db.get(Order, world["order"])
        return o.platform_discount, o.payment_status, o.total


def test_paying_online_gets_the_platform_discount_out_of_our_commission(
    user_client, session_factory, world, webhook, stripe_calls, promo
):
    promo(name="Pay in app 10% off")
    before = user_client.get("/user/orders", headers=world["user"]).json()[0]
    assert (before["online_offer"], before["online_offer_name"]) == ("1.00", "Pay in app 10% off")
    assert user_client.get(f"/voice/orders/{world['order']}", headers=world["user"]).json()["online_offer"] == "1.00"

    r = user_client.post(f"/voice/orders/{world['order']}/payment-intent", headers=world["user"])

    assert (r.json()["amount"], r.json()["platform_discount"], r.json()["promotion"]) == (1000, "1.00", "Pay in app 10% off")
    # The store still gets $11.00 - $1.50: the $1.00 discount comes out of our fee.
    assert stripe_calls["intents"][-1][1] == Decimal("10.00") and stripe_calls["fees"] == [Decimal("0.50")]

    pi = r.json()["client_secret"].removesuffix("_secret")
    webhook("payment_intent.succeeded", {"id": pi, "amount_received": 1000, "metadata": {"order_id": str(world["order"])}})

    assert _order(session_factory, world) == (Decimal("1.00"), "paid", Decimal("11.00"))
    mine = user_client.get("/user/orders", headers=world["user"]).json()[0]
    assert (mine["platform_discount"], mine["balance_due"]) == ("1.00", "0.00")


def test_the_discount_never_exceeds_our_commission(user_client, world, stripe_calls, promo):
    promo(name="$5 off", kind="amount_off", value="5")

    r = user_client.post(f"/voice/orders/{world['order']}/payment-intent", headers=world["user"])

    assert (r.json()["amount"], r.json()["platform_discount"]) == (950, "1.50")
    assert stripe_calls["fees"] == [Decimal("0.00")]


def test_it_stacks_on_the_store_discount(user_client, session_factory, world, promo):
    with session_factory() as db:
        o = db.get(Order, world["order"])
        # Store promotion already applied: $10.00 - $2.00 = $8.00, tax $0.80, commission 15% = $1.20.
        o.discount, o.tax, o.total, o.commission = Decimal("2.00"), Decimal("0.80"), Decimal("8.80"), Decimal("1.20")
        db.commit()
    promo()

    r = user_client.post(f"/voice/orders/{world['order']}/payment-intent", headers=world["user"])

    assert (r.json()["amount"], r.json()["platform_discount"]) == (800, "0.80")  # 10% of $8.00


def test_a_balance_after_a_staff_raise_gets_no_second_discount(
    store_client, user_client, world, webhook, stripe_calls, promo
):
    promo()
    _pay(user_client, world, webhook)  # $10.00 with $1.00 off
    store_client.post(f"/store/orders/{world['order']}/items", json={"menu_item_id": str(world["rice"])}, headers=world["store"])

    r = user_client.post(f"/voice/orders/{world['order']}/payment-intent", headers=world["user"])

    # $22.00 total - $1.00 discount - $10.00 paid; commission $3.00 - $0.50 taken - $1.00 given.
    assert (r.json()["amount"], r.json()["platform_discount"]) == (1100, "0.00")
    assert stripe_calls["fees"] == [Decimal("0.50"), Decimal("1.50")]


def test_first_order_only_and_per_customer_limits(admin_client, admin_headers, session_factory, world, promo):
    with session_factory() as db:
        o = db.get(Order, world["order"])
        earlier = Order(
            store_id=o.store_id, user_id=o.user_id, status="completed", channel="voice", short_code="OLD12",
            code_day=date(2026, 11, 1), subtotal=Decimal("5.00"), tax=Decimal("0"), total=Decimal("5.00"),
        )
        db.add(earlier)
        db.commit()
        earlier_id = earlier.id

    def offer():
        with session_factory() as db:
            found = platform_promotions.offer_for(db, db.get(Order, world["order"]))
            return found.promotion.name if found else None

    first = promo(name="First order", first_order_only=True)
    assert offer() is None  # the customer ordered before

    admin_client.patch(f"/admin/promotions/{first['id']}", json={"is_active": False}, headers=admin_headers)
    once = promo(name="Once each", per_user_limit=1)
    assert offer() == "Once each"

    with session_factory() as db:  # the earlier order already used it
        e = db.get(Order, earlier_id)
        e.platform_promotion_id, e.platform_discount = once["id"], Decimal("0.50")
        db.commit()
    assert offer() is None


def test_the_monthly_budget_caps_the_discount(user_client, session_factory, world, webhook, promo):
    promo(name="Budgeted", monthly_budget="0.60")

    r = user_client.post(f"/voice/orders/{world['order']}/payment-intent", headers=world["user"])

    assert r.json()["platform_discount"] == "0.60"


def test_commission_given_away_is_not_invoiced_and_counts_as_a_cost(
    admin_client, admin_headers, user_client, session_factory, world, webhook, promo
):
    promo()
    _pay(user_client, world, webhook)
    with session_factory() as db:
        db.get(Order, world["order"]).status = "completed"
        db.commit()
        # $0.50 taken through Stripe + $1.00 given as a discount = the whole $1.50.
        assert invoice_service.generate_drafts(db, date(2026, 11, 1)) == []

    totals = admin_client.get("/admin/stats/monthly", params={"month": "2026-11"}, headers=admin_headers).json()["totals"]

    assert (totals["commission"], totals["commission_online"], totals["platform_discounts"], totals["commission_to_invoice"]) == (
        "1.50", "0.50", "1.00", "0.00",
    )


def test_the_assistant_reads_the_online_offer_computed_in_code(session_factory, db_factory, world, promo):
    promo(name="App pay 10%")
    with session_factory() as db:
        order = db.get(Order, world["order"])
        order.status = "draft"
        store_id, user_id = order.store_id, order.user_id
        db.commit()
        prompt = load_store_voice_setup(db, db.get(Store, store_id)).system_prompt
    router = VoiceToolRouter(VoiceToolContext(db_factory=db_factory, store_id=store_id, user_id=user_id, order_id=world["order"]))

    summary = router.get_summary()["order"]

    assert summary["online_offer"]["say"] == "If you pay online in the app, you'll save $1.00 with App pay 10%."
    assert summary["total"] == 11.0  # the summary total does not include it
    assert "- App pay 10%: 10% off any order" in prompt and "NEVER calculate these yourself" in prompt


def test_admin_turns_promotions_off_and_cannot_delete_used_ones(
    admin_client, admin_headers, user_client, world, webhook, promo
):
    used = promo()
    _pay(user_client, world, webhook)

    r = admin_client.patch(f"/admin/promotions/{used['id']}", json={"is_active": False, "monthly_budget": "50"}, headers=admin_headers)
    assert (r.json()["is_active"], r.json()["monthly_budget"], r.json()["orders_count"]) == (False, "50.00", 1)
    assert admin_client.delete(f"/admin/promotions/{used['id']}", headers=admin_headers).status_code == 409
