"""The platform's monthly invoices to this store (sent ones only, not drafts)."""
from __future__ import annotations

import csv
import io
import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.store import get_current_store_web
from app.api.host_policy import require_host_policy
from app.core.errors import AppError
from app.db.session import get_db
from app.models.store import Store
from app.models.store_invoice import StoreInvoice
from app.schemas.common import Audience, PrincipalType
from app.schemas.invoice import InvoiceDetailOut, InvoiceOut
from app.services import invoice_service

router = APIRouter(
    prefix="/store/invoices",
    tags=["store-invoices"],
    dependencies=[Depends(require_host_policy(principal=PrincipalType.store, audience=Audience.web))],
)


def _get(db: Session, store: Store, invoice_id: uuid.UUID) -> StoreInvoice:
    invoice = db.get(StoreInvoice, invoice_id)
    if invoice is None or invoice.store_id != store.id or invoice.status == invoice_service.DRAFT:
        raise AppError(status_code=404, code="invoice_not_found", detail="Invoice not found")
    return invoice


@router.get("", response_model=list[InvoiceOut])
def list_invoices(
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> list[InvoiceOut]:
    rows = db.execute(
        select(StoreInvoice)
        .where(StoreInvoice.store_id == current_store.id)
        .where(StoreInvoice.status != invoice_service.DRAFT)
        .order_by(StoreInvoice.period.desc(), StoreInvoice.created_at.desc())
    ).scalars().all()
    return invoice_service.to_out(db, list(rows))


@router.get("/{invoice_id}", response_model=InvoiceDetailOut)
def get_invoice(
    invoice_id: uuid.UUID,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> InvoiceDetailOut:
    return invoice_service.to_detail(db, _get(db, current_store, invoice_id))


@router.get("/{invoice_id}/csv")
def invoice_csv(
    invoice_id: uuid.UUID,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> Response:
    detail = invoice_service.to_detail(db, _get(db, current_store, invoice_id))
    buf = io.StringIO()
    csv.writer(buf).writerows(invoice_service.csv_rows(detail))
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="voxeats-invoice-{detail.period}.csv"'},
    )
