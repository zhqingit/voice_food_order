from decimal import Decimal
from types import SimpleNamespace

import stripe

from app.core.config import settings
from app.services import payment_service


def test_customers_and_stores_get_fixed_payment_methods(monkeypatch):
    """Food is paid by card or Link only; invoices by card or ACH — whatever the Dashboard allows."""
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_x")
    seen = {}

    def intent(**kw):
        seen["intent"] = kw
        return SimpleNamespace(id="pi_1", client_secret="pi_1_secret")

    def invoice(**kw):
        seen["invoice"] = kw
        return SimpleNamespace(id="in_1")

    monkeypatch.setattr(stripe.PaymentIntent, "create", intent)
    monkeypatch.setattr(stripe.Invoice, "create", invoice)
    monkeypatch.setattr(stripe.InvoiceItem, "create", lambda **kw: None)
    monkeypatch.setattr(
        stripe.Invoice,
        "retrieve",
        lambda i: SimpleNamespace(id=i, status="open", due_date=None, hosted_invoice_url=None, invoice_pdf=None),
    )
    monkeypatch.setattr(stripe.Invoice, "send_invoice", lambda i: None)

    order = SimpleNamespace(id="o1")
    store = SimpleNamespace(id="s1", stripe_account_id="acct_1", stripe_charges_enabled=True)
    payment_service.create_payment_intent(order, store, amount_due=Decimal("11.00"), application_fee=Decimal("1.50"))
    payment_service.send_invoice(
        customer_id="cus_1", invoice_ref="r1", lines=[("x", Decimal("5.00"))], description="d", footer="f", days_until_due=15
    )

    assert seen["intent"]["payment_method_types"] == ["card", "link"]
    assert "automatic_payment_methods" not in seen["intent"]
    assert seen["invoice"]["payment_settings"] == {"payment_method_types": ["card", "us_bank_account"]}
