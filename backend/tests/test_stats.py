import uuid
from datetime import date, datetime
from decimal import Decimal

import pytest

from app.models.order import Order
from app.models.payment import Payment
from app.models.phone_call import PhoneCall
from app.models.store import Store
from app.models.voice_session import VoiceSession
from tests.test_commission import admin_headers  # noqa: F401  (shared fixture)

NOV = datetime(2026, 11, 10, 18, 0)  # naive UTC, as stored


@pytest.fixture()
def wok(session_factory):
    with session_factory() as db:
        store = Store(email="wok@example.com", password_hash="x", name="Hot Wok")
        db.add(store)
        db.flush()

        def order(channel, subtotal, status="completed", day=date(2026, 11, 10)):
            bps = 1000 if channel == "phone" else 1500
            o = Order(
                store_id=store.id, status=status, channel=channel, short_code=uuid.uuid4().hex[:5].upper(), code_day=day,
                subtotal=Decimal(subtotal), tax=Decimal("0.00"), total=Decimal(subtotal),
                commission_bps=bps, commission=Decimal(subtotal) * bps / 10000,
            )
            db.add(o)
            db.flush()
            return o

        paid_online = order("voice", "20.00")  # commission 3.00, taken through Stripe
        order("phone", "10.00")  # commission 1.00, paid at the store
        order("voice", "50.00", status="cancelled")  # not counted
        order("voice", "40.00", day=date(2026, 10, 31))  # last month
        db.add_all([
            Payment(order_id=paid_online.id, kind="charge", method="card", amount=Decimal("20.00"), status="succeeded",
                    stripe_id="pi_1", application_fee=Decimal("3.00"), stripe_fee=Decimal("0.88"), created_at=NOV),
            # Fee never fetched: estimated at 2.9% + 30¢ = 0.59.
            Payment(order_id=paid_online.id, kind="charge", method="card", amount=Decimal("10.00"), status="succeeded",
                    stripe_id="pi_2", created_at=NOV),
            VoiceSession(store_id=store.id, channel="voice", llm_cost=Decimal("0.400000"), started_at=NOV),
            PhoneCall(store_id=store.id, call_sid="CA1", end_reason="hangup", duration_seconds=90,
                      ai_cost=Decimal("0.100000"), telephony_cost=Decimal("0.0250"), started_at=NOV),
        ])
        db.commit()
        return store.id


def test_monthly_report_counts_completed_orders_and_this_months_costs(admin_client, admin_headers, wok):
    admin_client.post("/admin/stats/costs", json={"month": "2026-11", "category": "server", "amount": "20.00"}, headers=admin_headers)

    r = admin_client.get("/admin/stats/monthly", params={"month": "2026-11"}, headers=admin_headers)

    assert r.status_code == 200, r.text
    [row] = r.json()["stores"]
    assert (row["app"]["orders"], row["app"]["gmv"], row["app"]["commission"]) == (1, "20.00", "3.00")
    assert (row["phone"]["orders"], row["phone"]["commission"]) == (1, "1.00")
    assert (row["commission_online"], row["commission_to_invoice"]) == ("3.00", "1.00")
    assert (row["ai_cost"], row["telephony_cost"], row["stripe_fees"]) == ("0.50", "0.03", "1.47")
    assert (row["phone_calls"], row["phone_minutes"]) == (1, 2)
    assert (row["revenue"], row["costs"], row["net"]) == ("4.00", "2.00", "2.00")

    totals = r.json()["totals"]
    assert (totals["orders"], totals["fixed_costs"], totals["costs"], totals["net"]) == (2, "20.00", "22.00", "-18.00")


def test_fixed_costs_are_added_and_removed_and_the_report_exports_as_csv(admin_client, admin_headers, wok):
    added = admin_client.post(
        "/admin/stats/costs", json={"month": "2026-11", "category": "domain", "amount": "12.00", "note": " DNS "},
        headers=admin_headers,
    )
    assert added.status_code == 201 and added.json()["note"] == "DNS"

    csv = admin_client.get("/admin/stats/monthly.csv", params={"month": "2026-11"}, headers=admin_headers)
    assert csv.headers["content-disposition"] == 'attachment; filename="voxeats-2026-11.csv"'
    assert csv.text.splitlines()[1].startswith("Hot Wok,1,20.00,3.00,1,10.00,1.00")
    assert "fixed_costs,12.00" in csv.text

    admin_client.delete(f"/admin/stats/costs/{added.json()['id']}", headers=admin_headers)
    assert admin_client.get("/admin/stats/monthly", params={"month": "2026-11"}, headers=admin_headers).json()["fixed_costs"] == []
