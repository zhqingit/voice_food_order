from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

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
from app.models.refresh_session import RefreshSession
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.api.deps.user import get_current_user_mobile
from app.schemas.user.auth import LoginRequest, LogoutRequest, RefreshRequest, SignupRequest, TokenResponse
from app.schemas.common import Audience, PrincipalType

router = APIRouter(
    prefix="/user/auth",
    tags=["user-auth"],
    dependencies=[Depends(require_host_policy(principal=PrincipalType.user, audience=Audience.mobile))],
)


def _revoke_session(db: Session, session: RefreshSession) -> None:
    now = utcnow_naive()
    if session.revoked_at is None:
        session.revoked_at = now

    tokens = db.execute(select(RefreshToken).where(RefreshToken.session_id == session.id)).scalars().all()
    for token in tokens:
        if token.revoked_at is None:
            token.revoked_at = now


def _issue_tokens(db: Session, principal_id: uuid.UUID) -> TokenResponse:
    refresh_token = generate_refresh_token()
    refresh_hash = hash_refresh_token(refresh_token)

    session = RefreshSession(
        principal_type=str(PrincipalType.user),
        principal_id=principal_id,
        aud=str(Audience.mobile),
        expires_at=utcnow_naive() + timedelta(days=settings.refresh_token_ttl_days),
    )
    db.add(session)
    db.flush()

    db.add(RefreshToken(session_id=session.id, token_hash=refresh_hash))

    access_token = create_access_token(subject=str(principal_id), role=PrincipalType.user, audience=Audience.mobile)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, session_id=session.id)


@router.post("/signup", response_model=TokenResponse)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> TokenResponse:
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing is not None:
        raise AppError(status_code=409, code="email_taken", detail="Email already registered")

    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()

    tokens = _issue_tokens(db, user.id)
    db.commit()
    return tokens


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise AppError(status_code=401, code="invalid_credentials", detail="Invalid credentials")

    tokens = _issue_tokens(db, user.id)
    db.commit()
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    session: RefreshSession | None = db.get(RefreshSession, payload.session_id)
    if (
        session is None
        or session.revoked_at is not None
        or session.principal_type != str(PrincipalType.user)
        or session.aud != str(Audience.mobile)
    ):
        raise AppError(status_code=401, code="invalid_refresh", detail="Invalid refresh")
    if session.expires_at <= utcnow_naive():
        raise AppError(status_code=401, code="refresh_expired", detail="Refresh expired")

    incoming_hash = hash_refresh_token(payload.refresh_token)

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

    access_token = create_access_token(subject=str(session.principal_id), role=PrincipalType.user, audience=Audience.mobile)
    db.commit()

    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token, session_id=session.id)


@router.post("/logout")
def logout(
    payload: LogoutRequest,
    current_user: User = Depends(get_current_user_mobile),
    db: Session = Depends(get_db),
) -> dict:
    if payload.scope == "current":
        if payload.session_id is None:
            raise AppError(status_code=400, code="session_id_required", detail="session_id required for scope=current")

        session = db.get(RefreshSession, payload.session_id)
        if session is None or session.principal_id != current_user.id:
            return {"status": "ok"}

        _revoke_session(db, session)
        db.commit()
        return {"status": "ok"}

    sessions = db.execute(
        select(RefreshSession)
        .where(RefreshSession.principal_type == str(PrincipalType.user))
        .where(RefreshSession.principal_id == current_user.id)
        .where(RefreshSession.revoked_at.is_(None))
    ).scalars().all()

    for session in sessions:
        _revoke_session(db, session)

    db.commit()
    return {"status": "ok"}
