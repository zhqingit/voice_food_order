from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.admin import get_current_admin
from app.api.host_policy import require_host_policy
from app.core.config import settings
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    verify_password,
)
from app.core.time import utcnow_naive
from app.db.session import get_db
from app.models.admin import Admin
from app.models.refresh_session import RefreshSession
from app.models.refresh_token import RefreshToken
from app.schemas.admin.auth import AccessTokenResponse, AdminLoginRequest
from app.schemas.common import Audience, PrincipalType

router = APIRouter(
    prefix="/admin/auth",
    tags=["admin-auth"],
    dependencies=[Depends(require_host_policy(principal=PrincipalType.admin, audience=Audience.admin))],
)

_COOKIE_REFRESH = "admin_refresh_token"
_COOKIE_SESSION = "admin_session_id"


def _cookie_kwargs() -> dict:
    return {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "domain": settings.cookie_domain,
        "path": "/admin",
    }


def _set_session_cookies(response: Response, *, refresh_token: str, session_id: uuid.UUID) -> None:
    response.set_cookie(_COOKIE_REFRESH, refresh_token, **_cookie_kwargs())
    response.set_cookie(_COOKIE_SESSION, str(session_id), **_cookie_kwargs())


def _clear_session_cookies(response: Response) -> None:
    response.delete_cookie(_COOKIE_REFRESH, domain=settings.cookie_domain, path="/admin")
    response.delete_cookie(_COOKIE_SESSION, domain=settings.cookie_domain, path="/admin")


def _revoke_session(db: Session, session: RefreshSession) -> None:
    now = utcnow_naive()
    if session.revoked_at is None:
        session.revoked_at = now

    tokens = db.execute(select(RefreshToken).where(RefreshToken.session_id == session.id)).scalars().all()
    for token in tokens:
        if token.revoked_at is None:
            token.revoked_at = now


def _revoke_all_admin_sessions(db: Session, admin_id: uuid.UUID) -> None:
    sessions = db.execute(
        select(RefreshSession)
        .where(RefreshSession.principal_type == str(PrincipalType.admin))
        .where(RefreshSession.principal_id == admin_id)
        .where(RefreshSession.revoked_at.is_(None))
    ).scalars().all()

    for session in sessions:
        _revoke_session(db, session)


def _issue_admin_session(db: Session, admin_id: uuid.UUID) -> tuple[str, uuid.UUID]:
    refresh_token = generate_refresh_token()
    refresh_hash = hash_refresh_token(refresh_token)

    session = RefreshSession(
        principal_type=str(PrincipalType.admin),
        principal_id=admin_id,
        aud=str(Audience.admin),
        expires_at=utcnow_naive() + timedelta(days=settings.refresh_token_ttl_days),
    )
    db.add(session)
    db.flush()

    db.add(RefreshToken(session_id=session.id, token_hash=refresh_hash))
    return refresh_token, session.id


def _issue_admin_access_token(admin_id: uuid.UUID) -> str:
    return create_access_token(subject=str(admin_id), role=PrincipalType.admin, audience=Audience.admin)


@router.post("/login", response_model=AccessTokenResponse)
def login(payload: AdminLoginRequest, response: Response, db: Session = Depends(get_db)) -> AccessTokenResponse:
    admin = db.execute(select(Admin).where(Admin.email == payload.email)).scalar_one_or_none()
    if admin is None or not admin.is_active or not verify_password(payload.password, admin.password_hash):
        raise AppError(status_code=401, code="invalid_credentials", detail="Invalid credentials")

    _revoke_all_admin_sessions(db, admin.id)

    refresh_token, session_id = _issue_admin_session(db, admin.id)
    access_token = _issue_admin_access_token(admin.id)

    db.commit()

    _set_session_cookies(response, refresh_token=refresh_token, session_id=session_id)
    return AccessTokenResponse(access_token=access_token)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> AccessTokenResponse:
    refresh_token = request.cookies.get(_COOKIE_REFRESH)
    session_id_raw = request.cookies.get(_COOKIE_SESSION)
    if not refresh_token or not session_id_raw:
        raise AppError(status_code=401, code="invalid_refresh", detail="Invalid refresh")

    try:
        session_id = uuid.UUID(session_id_raw)
    except ValueError:
        raise AppError(status_code=401, code="invalid_refresh", detail="Invalid refresh")

    session: RefreshSession | None = db.get(RefreshSession, session_id)
    if (
        session is None
        or session.revoked_at is not None
        or session.principal_type != str(PrincipalType.admin)
        or session.aud != str(Audience.admin)
    ):
        raise AppError(status_code=401, code="invalid_refresh", detail="Invalid refresh")

    if session.expires_at <= utcnow_naive():
        raise AppError(status_code=401, code="refresh_expired", detail="Refresh expired")

    incoming_hash = hash_refresh_token(refresh_token)

    active_token = db.execute(
        select(RefreshToken)
        .where(RefreshToken.session_id == session.id)
        .where(RefreshToken.revoked_at.is_(None))
        .where(RefreshToken.replaced_by_id.is_(None))
        .order_by(RefreshToken.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    if active_token is None:
        raise AppError(status_code=401, code="invalid_refresh", detail="Invalid refresh")

    if active_token.token_hash != incoming_hash:
        seen_before = db.execute(
            select(RefreshToken)
            .where(RefreshToken.session_id == session.id)
            .where(RefreshToken.token_hash == incoming_hash)
        ).scalar_one_or_none()
        if seen_before is not None:
            _revoke_session(db, session)
            db.commit()
            raise AppError(status_code=401, code="refresh_reuse", detail="Refresh token reuse detected")

        raise AppError(status_code=401, code="invalid_refresh", detail="Invalid refresh")

    new_refresh_token = generate_refresh_token()
    new_hash = hash_refresh_token(new_refresh_token)

    new_token_row = RefreshToken(session_id=session.id, token_hash=new_hash)
    db.add(new_token_row)
    db.flush()

    active_token.revoked_at = utcnow_naive()
    active_token.replaced_by_id = new_token_row.id

    # Sliding expiration: extend session lifetime on each refresh
    session.expires_at = utcnow_naive() + timedelta(days=settings.refresh_token_ttl_days)

    access_token = _issue_admin_access_token(session.principal_id)
    db.commit()

    _set_session_cookies(response, refresh_token=new_refresh_token, session_id=session.id)
    return AccessTokenResponse(access_token=access_token)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    session_id_raw = request.cookies.get(_COOKIE_SESSION)
    if session_id_raw:
        try:
            session_id = uuid.UUID(session_id_raw)
            session = db.get(RefreshSession, session_id)
            if session is not None and session.principal_type == str(PrincipalType.admin):
                _revoke_session(db, session)
                db.commit()
        except ValueError:
            pass

    _clear_session_cookies(response)
    return {"status": "ok"}
