import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.models.order import Order
from app.models.payment import Payment
from app.models.store import Store
from app.services import payment_service
from tests.test_commission import admin_headers  # noqa: F401  (shared fixture)
from tests.test_order_payments import webhook  # noqa: F401  (shared fixture)

OCT = "2026-10"


@pytest.fixture()
def stripe_invoicing(monkeypatch):
    """Fake Stripe Invoicing: records what would be sent."""
    calls = {"sent": [], "voided": [], "paid_out_of_band": []}

    def send_invoice(*, customer_id, invoice_ref, lines, description, footer, days_until_due):
        calls["sent"].append(lines)
        return payment_service.SentInvoice(
            invoice_id=f"in_{len(calls['sent'])}", hosted_url="https://pay.example/in", pdf_url=None, due_date=date(2026, 11, 16)
        )

    monkeypatch.setattr(payment_service, "ensure_customer", lambda store: "cus_1")
    monkeypatch.setattr(payment_service, "send_invoice", send_invoice)
    monkeypatch.setattr(payment_service, "void_invoice", lambda i: calls["voided"].append(i))
    monkeypatch.setattr(payment_service, "mark_invoice_paid_out_of_band", lambda i: calls["paid_out_of_band"].append(i))
    monkeypatch.setattr(payment_service, "fetch_invoice_stripe_fee", lambda i: Decimal("1.84"))
    return calls


@pytest.fixture()
def wok(store_client, session_factory):
    r = store_client.post("/store/auth/signup", json={"email": "wok@example.com", "password": "password123", "name": "Hot Wok"})
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    store_id = uuid.UUID(store_client.get("/store/me", headers=headers).json()["id"])
    return {"id": store_id, "headers": headers}


def _order(session_factory, store_id, channel, subtotal, day, status="completed", fee_paid_online=None):
    with session_factory() as db:
        bps = 1000 if channel == "phone" else 1500
        o = Order(
            store_id=store_id, status=status, channel=channel, short_code=uuid.uuid4().hex[:5].upper(), code_day=day,
            subtotal=Decimal(subtotal), tax=Decimal("0.00"), total=Decimal(subtotal),
            commission_bps=bps, commission=(Decimal(subtotal) * bps / 10000).quantize(Decimal("0.01")),
        )
        db.add(o)
        db.flush()
        if fee_paid_online is not None:
            db.add(Payment(order_id=o.id, kind="charge", method="card", amount=Decimal(subtotal), status="succeeded",
                           stripe_id=f"pi_{o.id.hex[:8]}", application_fee=Decimal(fee_paid_online)))
        db.commit()
        return o.id


def _generate(admin_client, admin_headers, period=OCT):
    r = admin_client.post("/admin/invoices/generate", json={"period": period}, headers=admin_headers)
    assert r.status_code == 200, r.text
    return r.json()


def _detail(admin_client, admin_headers, invoice_id):
    return admin_client.get(f"/admin/invoices/{invoice_id}", headers=admin_headers).json()


def test_draft_bills_commission_not_taken_online_plus_the_monthly_fee(admin_client, admin_headers, session_factory, wok):
    with session_factory() as db:
        db.get(Store, wok["id"]).monthly_fee = Decimal("49.00")
        db.commit()
    _order(session_factory, wok["id"], "voice", "20.00", date(2026, 10, 3))  # 3.00
    _order(session_factory, wok["id"], "phone", "10.00", date(2026, 9, 30))  # 1.00, completed late
    _order(session_factory, wok["id"], "voice", "40.00", date(2026, 10, 5), fee_paid_online="6.00")  # all online
    _order(session_factory, wok["id"], "voice", "40.00", date(2026, 10, 6), fee_paid_online="2.00")  # 4.00 left
    _order(session_factory, wok["id"], "voice", "50.00", date(2026, 10, 7), status="cancelled")
    _order(session_factory, wok["id"], "voice", "50.00", date(2026, 8, 20))  # too old to pick up

    [draft] = _generate(admin_client, admin_headers)

    assert (draft["status"], draft["total"], draft["order_count"]) == ("draft", "57.00", 3)
    lines = _detail(admin_client, admin_headers, draft["id"])["lines"]
    assert [(line["kind"], line["amount"]) for line in lines] == [
        ("order", "1.00"), ("order", "3.00"), ("order", "4.00"), ("monthly_fee", "49.00"),
    ]
    assert (lines[2]["commission"], lines[2]["collected_online"]) == ("6.00", "2.00")
    assert _generate(admin_client, admin_headers) == []  # nothing billed twice


def test_small_totals_roll_over_to_the_next_month(admin_client, admin_headers, session_factory, wok):
    _order(session_factory, wok["id"], "phone", "5.00", date(2026, 10, 3))  # 0.50

    assert _generate(admin_client, admin_headers) == []

    _order(session_factory, wok["id"], "phone", "20.00", date(2026, 11, 3))  # 2.00
    [draft] = _generate(admin_client, admin_headers, "2026-11")
    assert (draft["total"], draft["order_count"]) == ("2.50", 2)


def test_deleting_a_draft_frees_its_orders_and_voiding_writes_them_off(admin_client, admin_headers, session_factory, wok):
    _order(session_factory, wok["id"], "voice", "20.00", date(2026, 10, 3))
    [draft] = _generate(admin_client, admin_headers)

    admin_client.delete(f"/admin/invoices/{draft['id']}", headers=admin_headers)
    [again] = _generate(admin_client, admin_headers)

    admin_client.post(f"/admin/invoices/{again['id']}/void", headers=admin_headers)
    assert _generate(admin_client, admin_headers) == []


def test_reviewed_invoice_is_sent_paid_and_shown_to_the_store(
    admin_client, store_client, admin_headers, session_factory, wok, stripe_invoicing, webhook
):
    _order(session_factory, wok["id"], "voice", "20.00", date(2026, 10, 3))
    _order(session_factory, wok["id"], "voice", "10.00", date(2026, 10, 4))
    _order(session_factory, wok["id"], "phone", "10.00", date(2026, 10, 4))
    [draft] = _generate(admin_client, admin_headers)
    url = f"/admin/invoices/{draft['id']}"

    assert store_client.get("/store/invoices", headers=wok["headers"]).json() == []  # drafts stay private
    r = admin_client.post(f"{url}/adjustments", json={"description": "Launch promo credit", "amount": "-1.50"}, headers=admin_headers)
    assert r.json()["total"] == "4.00"

    sent = admin_client.post(f"{url}/send", headers=admin_headers).json()

    assert (sent["status"], sent["due_date"]) == ("open", "2026-11-16")
    assert stripe_invoicing["sent"] == [[
        ("Commission on app orders paid at the store, October 2026 (2 orders)", Decimal("4.50")),
        ("Commission on phone orders paid at the store, October 2026 (1 order)", Decimal("1.00")),
        ("Launch promo credit", Decimal("-1.50")),
    ]]
    assert admin_client.post(f"{url}/adjustments", json={"description": "x", "amount": "1"}, headers=admin_headers).status_code == 409

    webhook("invoice.paid", {"id": "in_1", "paid_out_of_band": False})

    [mine] = store_client.get("/store/invoices", headers=wok["headers"]).json()
    assert (mine["status"], mine["total"], mine["hosted_url"]) == ("paid", "4.00", "https://pay.example/in")
    detail = store_client.get(f"/store/invoices/{mine['id']}", headers=wok["headers"]).json()
    assert len([line for line in detail["lines"] if line["kind"] == "order"]) == 3
    csv = store_client.get(f"/store/invoices/{mine['id']}/csv", headers=wok["headers"])
    assert csv.text.splitlines()[1].startswith("order,") and csv.text.splitlines()[-1] == "total,,,,,,,,4.00,"

    totals = admin_client.get("/admin/stats/monthly", params={"month": OCT}, headers=admin_headers).json()["totals"]
    # Fee: 1.84 for the payment + 0.4% Stripe Invoicing (0.02).
    assert (totals["invoiced"], totals["invoice_paid"], totals["invoice_fees"]) == ("4.00", "4.00", "1.86")


def test_store_cannot_see_another_stores_invoice(admin_client, store_client, admin_headers, session_factory, wok, stripe_invoicing):
    _order(session_factory, wok["id"], "voice", "20.00", date(2026, 10, 3))
    [draft] = _generate(admin_client, admin_headers)
    admin_client.post(f"/admin/invoices/{draft['id']}/send", headers=admin_headers)

    r = store_client.post("/store/auth/signup", json={"email": "other@example.com", "password": "password123", "name": "Other"})
    other = {"Authorization": f"Bearer {r.json()['access_token']}"}

    assert store_client.get(f"/store/invoices/{draft['id']}", headers=other).status_code == 404
