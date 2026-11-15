from __future__ import annotations

import csv
import io
import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps.admin import get_current_admin
from app.api.host_policy import require_host_policy
from app.core.errors import AppError
from app.db.session import get_db
from app.models.admin import Admin
from app.models.platform_cost import PlatformCost
from app.schemas.admin.stats import MonthlyStatsOut, PlatformCostCreate, PlatformCostOut
from app.schemas.common import Audience, PrincipalType
from app.services import months, stats_service

router = APIRouter(
    prefix="/admin/stats",
    tags=["admin-stats"],
    dependencies=[Depends(require_host_policy(principal=PrincipalType.admin, audience=Audience.admin))],
)

MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


def _month_or_current(month: str | None) -> str:
    return month or months.platform_today().strftime("%Y-%m")


@router.get("/monthly", response_model=MonthlyStatsOut)
def monthly(
    month: str | None = Query(default=None, pattern=MONTH_PATTERN),
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> MonthlyStatsOut:
    return stats_service.monthly_report(db, _month_or_current(month))


@router.get("/monthly.csv")
def monthly_csv(
    month: str | None = Query(default=None, pattern=MONTH_PATTERN),
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Response:
    report = stats_service.monthly_report(db, _month_or_current(month))
    buf = io.StringIO()
    csv.writer(buf).writerows(stats_service.csv_rows(report))
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="voxeats-{report.month}.csv"'},
    )


@router.post("/costs", response_model=PlatformCostOut, status_code=201)
def add_cost(
    payload: PlatformCostCreate,
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> PlatformCostOut:
    cost = PlatformCost(
        month=stats_service.parse_month(payload.month),
        category=payload.category,
        amount=payload.amount,
        note=(payload.note or "").strip() or None,
    )
    db.add(cost)
    db.commit()
    return stats_service.cost_out(cost)


@router.delete("/costs/{cost_id}", status_code=204)
def delete_cost(
    cost_id: uuid.UUID,
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Response:
    cost = db.get(PlatformCost, cost_id)
    if cost is None:
        raise AppError(status_code=404, code="cost_not_found", detail="Cost not found")
    db.delete(cost)
    db.commit()
    return Response(status_code=204)
