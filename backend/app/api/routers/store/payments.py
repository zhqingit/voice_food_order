from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.store import get_current_store_web
from app.api.host_policy import require_host_policy
from app.core.errors import AppError
from app.db.session import get_db
from app.models.store import Store
from app.schemas.common import Audience, PrincipalType
from app.schemas.store.payments import (
    PaymentConnectRequest,
    PaymentConnectResponse,
    PaymentStatusResponse,
)
from app.services import payment_service

log = logging.getLogger(__name__)

router = APIRouter(
    prefix="/store/payments",
    tags=["store-payments"],
    dependencies=[Depends(require_host_policy(principal=PrincipalType.store, audience=Audience.web))],
)


@router.post("/connect", response_model=PaymentConnectResponse)
def connect(
    payload: PaymentConnectRequest,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> PaymentConnectResponse:
    """Create-or-reuse the store's Express account and return an onboarding URL."""
    if not current_store.stripe_account_id:
        account_id = payment_service.create_express_account(current_store)
        current_store.stripe_account_id = account_id
        db.add(current_store)
        db.commit()
        db.refresh(current_store)

    url = payment_service.create_account_link(
        current_store.stripe_account_id,
        refresh_url=str(payload.refresh_url),
        return_url=str(payload.return_url),
    )
    return PaymentConnectResponse(url=url, account_id=current_store.stripe_account_id)


@router.get("/status", response_model=PaymentStatusResponse)
def status(
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> PaymentStatusResponse:
    """Payment-readiness + commission for the store's own portal (read-only)."""
    connected = current_store.stripe_account_id is not None
    charges_enabled = current_store.stripe_charges_enabled
    details_submitted = False

    # Live sync when connected: keeps the badge correct even before the
    # account.updated webhook fires (and works in dev without webhooks set up).
    if connected:
        try:
            live = payment_service.fetch_account_status(current_store.stripe_account_id)
            details_submitted = live.details_submitted
            if live.charges_enabled != current_store.stripe_charges_enabled:
                current_store.stripe_charges_enabled = live.charges_enabled
                db.add(current_store)
                db.commit()
            charges_enabled = live.charges_enabled
        except AppError as exc:
            log.warning("store.payments.status: live fetch failed: %s", exc.detail)

    return PaymentStatusResponse(
        connected=connected,
        charges_enabled=charges_enabled,
        details_submitted=details_submitted,
        fee_bps=payment_service.resolve_fee_bps(current_store),
    )
