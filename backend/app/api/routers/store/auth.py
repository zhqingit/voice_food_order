from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.store import get_current_store_web
from app.api.host_policy import require_host_policy
from app.core.config import settings
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.core.time import utcnow_naive
from app.db.session import get_db
from app.models.store import Store
from app.models.refresh_session import RefreshSession
from app.models.refresh_token import RefreshToken
from app.schemas.common import Audience, PrincipalType
from app.schemas.store.auth import AccessTokenResponse, StoreLoginRequest, StoreSignupRequest

router = APIRouter(
    prefix="/store/auth",
    tags=["store-auth"],
    dependencies=[Depends(require_host_policy(principal=PrincipalType.store, audience=Audience.web))],
)

_COOKIE_REFRESH = "store_refresh_token"
_COOKIE_SESSION = "store_session_id"


def _cookie_kwargs() -> dict:
    return {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "domain": settings.cookie_domain,
        "path": "/store",
    }


def _set_session_cookies(response: Response, *, refresh_token: str, session_id: uuid.UUID) -> None:
    response.set_cookie(_COOKIE_REFRESH, refresh_token, **_cookie_kwargs())
    response.set_cookie(_COOKIE_SESSION, str(session_id), **_cookie_kwargs())


def _clear_session_cookies(response: Response) -> None:
    response.delete_cookie(_COOKIE_REFRESH, domain=settings.cookie_domain, path="/store")
    response.delete_cookie(_COOKIE_SESSION, domain=settings.cookie_domain, path="/store")


def _revoke_session(db: Session, session: RefreshSession) -> None:
    now = utcnow_naive()
    if session.revoked_at is None:
        session.revoked_at = now

    tokens = db.execute(select(RefreshToken).where(RefreshToken.session_id == session.id)).scalars().all()
    for token in tokens:
        if token.revoked_at is None:
            token.revoked_at = now


def _revoke_all_store_sessions(db: Session, store_id: uuid.UUID) -> None:
    sessions = db.execute(
        select(RefreshSession)
        .where(RefreshSession.principal_type == str(PrincipalType.store))
        .where(RefreshSession.principal_id == store_id)
        .where(RefreshSession.revoked_at.is_(None))
    ).scalars().all()

    for session in sessions:
        _revoke_session(db, session)


def _issue_store_session(db: Session, store_id: uuid.UUID) -> tuple[str, uuid.UUID]:
    refresh_token = generate_refresh_token()
    refresh_hash = hash_refresh_token(refresh_token)

    session = RefreshSession(
        principal_type=str(PrincipalType.store),
        principal_id=store_id,
        aud=str(Audience.web),
        expires_at=utcnow_naive() + timedelta(days=settings.refresh_token_ttl_days),
    )
    db.add(session)
    db.flush()

    db.add(RefreshToken(session_id=session.id, token_hash=refresh_hash))
    return refresh_token, session.id


def _issue_store_access_token(store_id: uuid.UUID) -> str:
    return create_access_token(subject=str(store_id), role=PrincipalType.store, audience=Audience.web)


@router.post("/signup", response_model=AccessTokenResponse)
def signup(payload: StoreSignupRequest, response: Response, db: Session = Depends(get_db)) -> AccessTokenResponse:
    existing = db.execute(select(Store).where(Store.email == payload.email)).scalar_one_or_none()
    if existing is not None:
        raise AppError(status_code=409, code="email_taken", detail="Email already registered")

    store = Store(
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(store)
    db.flush()

    # Enforce single active session for store.
    _revoke_all_store_sessions(db, store.id)

    refresh_token, session_id = _issue_store_session(db, store.id)
    access_token = _issue_store_access_token(store.id)

    db.commit()

    _set_session_cookies(response, refresh_token=refresh_token, session_id=session_id)
    return AccessTokenResponse(access_token=access_token)


@router.post("/login", response_model=AccessTokenResponse)
def login(payload: StoreLoginRequest, response: Response, db: Session = Depends(get_db)) -> AccessTokenResponse:
    store = db.execute(select(Store).where(Store.email == payload.email)).scalar_one_or_none()
    if store is None or not store.is_active or not verify_password(payload.password, store.password_hash):
        raise AppError(status_code=401, code="invalid_credentials", detail="Invalid credentials")

    _revoke_all_store_sessions(db, store.id)

    refresh_token, session_id = _issue_store_session(db, store.id)
    access_token = _issue_store_access_token(store.id)

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
        or session.principal_type != str(PrincipalType.store)
        or session.aud != str(Audience.web)
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

    access_token = _issue_store_access_token(session.principal_id)
    db.commit()

    _set_session_cookies(response, refresh_token=new_refresh_token, session_id=session.id)
    return AccessTokenResponse(access_token=access_token)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    _: Store = Depends(get_current_store_web),
    db: Session = Depends(get_db),
) -> dict:
    # Revoke current session if present.
    session_id_raw = request.cookies.get(_COOKIE_SESSION)
    if session_id_raw:
        try:
            session_id = uuid.UUID(session_id_raw)
            session = db.get(RefreshSession, session_id)
            if session is not None and session.principal_type == str(PrincipalType.store):
                _revoke_session(db, session)
                db.commit()
        except ValueError:
            pass

    _clear_session_cookies(response)
    return {"status": "ok"}
