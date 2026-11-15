from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.admin import get_current_admin
from app.api.host_policy import require_host_policy
from app.core.errors import AppError
from app.db.session import get_db
from app.models.admin import Admin
from app.models.store import Store
from app.models.store_invoice import StoreInvoice
from app.schemas.common import Audience, PrincipalType
from app.schemas.invoice import InvoiceAdjustmentCreate, InvoiceDetailOut, InvoiceGenerateRequest, InvoiceOut
from app.services import invoice_service, stats_service

router = APIRouter(
    prefix="/admin/invoices",
    tags=["admin-invoices"],
    dependencies=[Depends(require_host_policy(principal=PrincipalType.admin, audience=Audience.admin))],
)


def _get(db: Session, invoice_id: uuid.UUID) -> StoreInvoice:
    invoice = db.get(StoreInvoice, invoice_id, with_for_update=True)
    if invoice is None:
        raise AppError(status_code=404, code="invoice_not_found", detail="Invoice not found")
    return invoice


@router.get("", response_model=list[InvoiceOut])
def list_invoices(
    period: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[InvoiceOut]:
    rows = db.execute(
        select(StoreInvoice)
        .join(Store, Store.id == StoreInvoice.store_id)
        .where(StoreInvoice.period == stats_service.parse_month(period))
        .order_by(Store.name, StoreInvoice.created_at)
    ).scalars().all()
    return invoice_service.to_out(db, list(rows))


@router.post("/generate", response_model=list[InvoiceOut])
def generate(
    payload: InvoiceGenerateRequest,
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[InvoiceOut]:
    """Create the missing drafts for a month; returns the ones created."""
    created = invoice_service.generate_drafts(db, stats_service.parse_month(payload.period))
    db.commit()
    return invoice_service.to_out(db, created)


@router.get("/{invoice_id}", response_model=InvoiceDetailOut)
def get_invoice(
    invoice_id: uuid.UUID,
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> InvoiceDetailOut:
    return invoice_service.to_detail(db, _get(db, invoice_id))


@router.post("/{invoice_id}/adjustments", response_model=InvoiceDetailOut)
def add_adjustment(
    invoice_id: uuid.UUID,
    payload: InvoiceAdjustmentCreate,
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> InvoiceDetailOut:
    invoice = _get(db, invoice_id)
    invoice_service.add_adjustment(db, invoice, description=payload.description.strip(), amount=payload.amount)
    db.commit()
    return invoice_service.to_detail(db, invoice)


@router.delete("/{invoice_id}/adjustments/{line_id}", response_model=InvoiceDetailOut)
def remove_adjustment(
    invoice_id: uuid.UUID,
    line_id: uuid.UUID,
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> InvoiceDetailOut:
    invoice = _get(db, invoice_id)
    invoice_service.remove_adjustment(db, invoice, line_id)
    db.commit()
    return invoice_service.to_detail(db, invoice)


@router.post("/{invoice_id}/send", response_model=InvoiceDetailOut)
def send(
    invoice_id: uuid.UUID,
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> InvoiceDetailOut:
    invoice = _get(db, invoice_id)
    invoice_service.send(db, invoice)
    db.commit()
    return invoice_service.to_detail(db, invoice)


@router.post("/{invoice_id}/void", response_model=InvoiceDetailOut)
def void(
    invoice_id: uuid.UUID,
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> InvoiceDetailOut:
    invoice = _get(db, invoice_id)
    invoice_service.void(db, invoice)
    db.commit()
    return invoice_service.to_detail(db, invoice)


@router.post("/{invoice_id}/mark-paid", response_model=InvoiceDetailOut)
def mark_paid(
    invoice_id: uuid.UUID,
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> InvoiceDetailOut:
    invoice = _get(db, invoice_id)
    invoice_service.mark_paid_by_admin(db, invoice)
    db.commit()
    return invoice_service.to_detail(db, invoice)


@router.delete("/{invoice_id}", status_code=204)
def delete_draft(
    invoice_id: uuid.UUID,
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Response:
    invoice_service.delete_draft(db, _get(db, invoice_id))
    db.commit()
    return Response(status_code=204)
