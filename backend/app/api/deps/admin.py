from __future__ import annotations

import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.host_policy import require_host_policy
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.admin import Admin
from app.schemas.common import Audience, PrincipalType

_security = HTTPBearer(auto_error=False)


def get_current_admin(
    _: object = Depends(require_host_policy(principal=PrincipalType.admin, audience=Audience.admin)),
    creds: HTTPAuthorizationCredentials | None = Depends(_security),
    db: Session = Depends(get_db),
) -> Admin:
    if creds is None or creds.scheme.lower() != "bearer":
        raise AppError(status_code=401, code="not_authenticated", detail="Not authenticated")

    try:
        decoded = decode_access_token(creds.credentials)
    except ValueError:
        raise AppError(status_code=401, code="invalid_access_token", detail="Invalid token")

    if decoded.role != PrincipalType.admin or decoded.audience != Audience.admin:
        raise AppError(status_code=403, code="wrong_portal", detail="Wrong portal")

    try:
        admin_id = uuid.UUID(decoded.subject)
    except ValueError:
        raise AppError(status_code=401, code="invalid_access_token", detail="Invalid token")

    admin = db.get(Admin, admin_id)
    if admin is None or not admin.is_active:
        raise AppError(status_code=401, code="invalid_access_token", detail="Invalid token")

    return admin
