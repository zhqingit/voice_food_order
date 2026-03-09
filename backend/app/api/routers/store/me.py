from __future__ import annotations

import os
from datetime import time as dt_time
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.store import get_current_store_web
from app.api.host_policy import require_host_policy
from app.core.errors import AppError
from app.db.session import get_db
from app.models.store import Store
from app.models.store_hours import StoreHours
from app.schemas.common import Audience, PrincipalType
from app.schemas.store.hours import DayHours, StoreHoursUpdate
from app.schemas.store.store import StoreOut, StoreUpdate

router = APIRouter(
    prefix="/store",
    tags=["store"],
    dependencies=[Depends(require_host_policy(principal=PrincipalType.store, audience=Audience.web))],
)


def _store_out(s: Store) -> StoreOut:
    return StoreOut(
        id=s.id,
        name=s.name,
        phone=s.phone,
        address_line1=s.address_line1,
        address_line2=s.address_line2,
        city=s.city,
        state=s.state,
        postal_code=s.postal_code,
        country=s.country,
        timezone=s.timezone,
        allow_pickup=s.allow_pickup,
        allow_delivery=s.allow_delivery,
        min_order_amount=s.min_order_amount,
        tax_rate=s.tax_rate,
        voice_tone=s.voice_tone,
        logo_url=s.logo_url,
        email=s.email,
        created_at=s.created_at,
    )


@router.get("/me", response_model=StoreOut)
def me(current_store: Store = Depends(get_current_store_web)) -> StoreOut:
    return _store_out(current_store)


@router.patch("/me", response_model=StoreOut)
def update_me(
    payload: StoreUpdate,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> StoreOut:
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(current_store, key, value)

    db.add(current_store)
    db.commit()
    db.refresh(current_store)
    return _store_out(current_store)


@router.post("/me/logo", response_model=StoreOut)
async def upload_logo(
    file: UploadFile = File(...),
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> StoreOut:
    ct = (file.content_type or "").lower()
    ext_from_name = (file.filename or "").rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
    image_exts = {"png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "ico"}
    if not ct.startswith("image/") and ext_from_name not in image_exts:
        raise AppError(status_code=400, code="invalid_file_type", detail="File must be an image")

    contents = await file.read()
    if len(contents) > 2 * 1024 * 1024:
        raise AppError(status_code=400, code="file_too_large", detail="File size must be <= 2MB")

    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "png"

    backend_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    upload_dir = backend_root / "uploads" / "logos"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{current_store.id}.{ext}"
    file_path.write_bytes(contents)

    current_store.logo_url = f"/uploads/logos/{current_store.id}.{ext}"
    db.add(current_store)
    db.commit()
    db.refresh(current_store)
    return _store_out(current_store)


# ── Store Hours ──────────────────────────────────────────────────────────────

def _row_to_day(row: StoreHours) -> DayHours:
    return DayHours(
        day_of_week=row.day_of_week,
        open_time=row.open_time.strftime("%H:%M"),
        close_time=row.close_time.strftime("%H:%M"),
        is_closed=row.is_closed,
    )


@router.get("/me/hours", response_model=list[DayHours])
def get_hours(
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> list[DayHours]:
    rows = (
        db.execute(
            select(StoreHours)
            .where(StoreHours.store_id == current_store.id)
            .order_by(StoreHours.day_of_week)
        )
        .scalars()
        .all()
    )
    return [_row_to_day(r) for r in rows]


@router.put("/me/hours", response_model=list[DayHours])
def update_hours(
    payload: StoreHoursUpdate,
    current_store: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> list[DayHours]:
    existing = db.execute(
        select(StoreHours).where(StoreHours.store_id == current_store.id)
    ).scalars().all()
    for row in existing:
        db.delete(row)
    db.flush()

    new_rows: list[StoreHours] = []
    for day in payload.hours:
        parts_open = day.open_time.split(":")
        parts_close = day.close_time.split(":")
        row = StoreHours(
            store_id=current_store.id,
            day_of_week=day.day_of_week,
            open_time=dt_time(int(parts_open[0]), int(parts_open[1])),
            close_time=dt_time(int(parts_close[0]), int(parts_close[1])),
            is_closed=day.is_closed,
        )
        db.add(row)
        new_rows.append(row)

    db.commit()
    for r in new_rows:
        db.refresh(r)
    return [_row_to_day(r) for r in sorted(new_rows, key=lambda r: r.day_of_week)]
