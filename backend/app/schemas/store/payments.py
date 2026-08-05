from __future__ import annotations

from pydantic import AnyHttpUrl, BaseModel


class PaymentConnectRequest(BaseModel):
    # Where Stripe redirects the store after onboarding completes / needs a
    # retry. The store portal supplies its own URLs.
    return_url: AnyHttpUrl
    refresh_url: AnyHttpUrl


class PaymentConnectResponse(BaseModel):
    url: str  # one-time Stripe-hosted onboarding URL
    account_id: str


class PaymentStatusResponse(BaseModel):
    connected: bool  # a Stripe account has been created for this store
    charges_enabled: bool  # store can accept online payment
    details_submitted: bool  # store finished the onboarding form
    fee_bps: int  # commission applied to this store's orders
