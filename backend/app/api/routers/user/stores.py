from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.host_policy import require_host_policy
from app.db.session import get_db
from app.models.store import Store
from app.schemas.common import Audience, PrincipalType
from app.schemas.store.store import StorePublicOut

router = APIRouter(
    prefix="/user/stores",
    tags=["user-stores"],
    dependencies=[Depends(require_host_policy(principal=PrincipalType.user, audience=Audience.mobile))],
)


def _store_public_out(store: Store) -> StorePublicOut:
    return StorePublicOut(
        id=store.id,
        name=store.name,
        phone=store.phone,
        address_line1=store.address_line1,
        city=store.city,
        state=store.state,
        country=store.country,
        timezone=store.timezone,
        allow_pickup=store.allow_pickup,
        allow_delivery=store.allow_delivery,
        min_order_amount=store.min_order_amount,
    )


@router.get("", response_model=list[StorePublicOut])
def list_stores(db: Session = Depends(get_db)) -> list[StorePublicOut]:
    stores = (
        db.execute(select(Store).where(Store.is_active == True).order_by(Store.created_at.desc()))  # noqa: E712
        .scalars()
        .all()
    )
    return [_store_public_out(store) for store in stores]
