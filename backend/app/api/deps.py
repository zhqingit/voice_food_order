from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.core.errors import AppError
from app.db.session import get_db
from app.models.user import User

_security = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_security),
    db: Session = Depends(get_db),
) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise AppError(status_code=401, code="not_authenticated", detail="Not authenticated")

    try:
        decoded = decode_access_token(creds.credentials)
    except ValueError:
        raise AppError(status_code=401, code="invalid_access_token", detail="Invalid token")

    try:
        user_id = uuid.UUID(decoded.subject)
    except ValueError:
        raise AppError(status_code=401, code="invalid_access_token", detail="Invalid token")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AppError(status_code=401, code="invalid_access_token", detail="Invalid token")

    return user
