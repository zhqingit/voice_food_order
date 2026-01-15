from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps.user import get_current_user_mobile
from app.api.host_policy import require_host_policy
from app.models.user import User
from app.schemas.common import Audience, PrincipalType
from app.schemas.user.user import UserOut

router = APIRouter(
    prefix="/user",
    tags=["user"],
    dependencies=[Depends(require_host_policy(principal=PrincipalType.user, audience=Audience.mobile))],
)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user_mobile)) -> UserOut:
    return UserOut(id=current_user.id, email=current_user.email, created_at=current_user.created_at)
