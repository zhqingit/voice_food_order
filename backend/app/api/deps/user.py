from __future__ import annotations

import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.host_policy import require_host_policy
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Audience, PrincipalType

_security = HTTPBearer(auto_error=False)


def get_current_user_mobile(
    _: object = Depends(require_host_policy(principal=PrincipalType.user, audience=Audience.mobile)),
    creds: HTTPAuthorizationCredentials | None = Depends(_security),
    db: Session = Depends(get_db),
) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise AppError(status_code=401, code="not_authenticated", detail="Not authenticated")

    try:
        decoded = decode_access_token(creds.credentials)
    except ValueError:
        raise AppError(status_code=401, code="invalid_access_token", detail="Invalid token")

    if decoded.role != PrincipalType.user or decoded.audience != Audience.mobile:
        raise AppError(status_code=403, code="wrong_portal", detail="Wrong portal")

    try:
        user_id = uuid.UUID(decoded.subject)
    except ValueError:
        raise AppError(status_code=401, code="invalid_access_token", detail="Invalid token")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AppError(status_code=401, code="invalid_access_token", detail="Invalid token")

    return user
