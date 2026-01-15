from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps.store import get_current_store_web
from app.api.host_policy import require_host_policy
from app.models.store import Store
from app.schemas.common import Audience, PrincipalType
from app.schemas.store.store import StoreOut

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
        email=current_store.email,
        created_at=current_store.created_at,
    )
