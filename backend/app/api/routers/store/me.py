from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.store import get_current_store_web
from app.api.host_policy import require_host_policy
from app.db.session import get_db
from app.models.store import Store
from app.schemas.common import Audience, PrincipalType
from app.schemas.store.store import StoreOut, StoreUpdate

router = APIRouter(
    prefix="/store",
    tags=["store"],
    dependencies=[Depends(require_host_policy(principal=PrincipalType.store, audience=Audience.web))],
)


@router.get("/me", response_model=StoreOut)
def me(current_store: Store = Depends(get_current_store_web)) -> StoreOut:
    return StoreOut(
        id=current_store.id,
        name=current_store.name,
        phone=current_store.phone,
        address_line1=current_store.address_line1,
        address_line2=current_store.address_line2,
        city=current_store.city,
        state=current_store.state,
        postal_code=current_store.postal_code,
        country=current_store.country,
        timezone=current_store.timezone,
        allow_pickup=current_store.allow_pickup,
        allow_delivery=current_store.allow_delivery,
        min_order_amount=current_store.min_order_amount,
        email=current_store.email,
        created_at=current_store.created_at,
    )


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

    return StoreOut(
        id=current_store.id,
        name=current_store.name,
        phone=current_store.phone,
        address_line1=current_store.address_line1,
        address_line2=current_store.address_line2,
        city=current_store.city,
        state=current_store.state,
        postal_code=current_store.postal_code,
        country=current_store.country,
        timezone=current_store.timezone,
        allow_pickup=current_store.allow_pickup,
        allow_delivery=current_store.allow_delivery,
        min_order_amount=current_store.min_order_amount,
        email=current_store.email,
        created_at=current_store.created_at,
    )
