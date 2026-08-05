from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.admin import get_current_admin
from app.api.host_policy import require_host_policy
from app.core.errors import AppError
from app.db.session import get_db
from app.models.admin import Admin
from app.models.store import Store
from app.schemas.admin.store import AdminStoreDetailOut, AdminStoreOut, AdminStoreUpdate
from app.schemas.common import Audience, PrincipalType
from app.services import payment_service

log = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/stores",
    tags=["admin-stores"],
    dependencies=[Depends(require_host_policy(principal=PrincipalType.admin, audience=Audience.admin))],
)


def _store_out(s: Store) -> AdminStoreOut:
    return AdminStoreOut(
        id=s.id,
        name=s.name,
        email=s.email,
        phone=s.phone,
        is_published=s.is_published,
        is_approved=s.is_approved,
        is_active=s.is_active,
        stripe_account_id=s.stripe_account_id,
        stripe_charges_enabled=s.stripe_charges_enabled,
        platform_fee_bps=s.platform_fee_bps,
        effective_fee_bps=payment_service.resolve_fee_bps(s),
        created_at=s.created_at,
    )


def _detail_out(s: Store) -> AdminStoreDetailOut:
    return AdminStoreDetailOut(**_store_out(s).model_dump())


def _get_store_or_404(db: Session, store_id: uuid.UUID) -> Store:
    store = db.get(Store, store_id)
    if store is None:
        raise AppError(status_code=404, code="store_not_found", detail="Store not found")
    return store


@router.get("", response_model=list[AdminStoreOut])
def list_stores(
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[AdminStoreOut]:
    rows = db.execute(select(Store).order_by(Store.created_at.desc())).scalars().all()
    return [_store_out(s) for s in rows]


@router.get("/{store_id}", response_model=AdminStoreDetailOut)
def get_store(
    store_id: uuid.UUID,
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminStoreDetailOut:
    store = _get_store_or_404(db, store_id)
    detail = _detail_out(store)

    # Best-effort live Stripe status. The cached stripe_charges_enabled (kept
    # fresh by the account.updated webhook) is the source of truth; this just
    # enriches the admin view and never fails the request.
    if store.stripe_account_id:
        try:
            status = payment_service.fetch_account_status(store.stripe_account_id)
            detail.stripe_details_submitted = status.details_submitted
            detail.stripe_payouts_enabled = status.payouts_enabled
        except AppError as exc:
            log.warning("admin.get_store: live Stripe status fetch failed for %s: %s", store_id, exc.detail)

    return detail


@router.patch("/{store_id}", response_model=AdminStoreDetailOut)
def update_store(
    store_id: uuid.UUID,
    payload: AdminStoreUpdate,
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminStoreDetailOut:
    store = _get_store_or_404(db, store_id)

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(store, key, value)

    db.add(store)
    db.commit()
    db.refresh(store)
    return _detail_out(store)
