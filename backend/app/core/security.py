from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.schemas.common import Audience, PrincipalType

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password, password_hash)


def create_access_token(
    *,
    subject: str,
    role: PrincipalType,
    audience: Audience,
    ttl_minutes: int | None = None,
) -> str:
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=ttl_minutes or settings.access_token_ttl_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": str(role),
        "aud": str(audience),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@dataclass(frozen=True)
class DecodedAccessToken:
    subject: str
    role: PrincipalType
    audience: Audience


def decode_access_token(token: str) -> DecodedAccessToken:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"verify_aud": False},
        )
    except JWTError as exc:
        raise ValueError("invalid token") from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise ValueError("invalid token")

    role_raw = payload.get("role")
    aud_raw = payload.get("aud")
    try:
        role = PrincipalType(str(role_raw))
        audience = Audience(str(aud_raw))
    except Exception as exc:
        raise ValueError("invalid token") from exc

    return DecodedAccessToken(subject=subject, role=role, audience=audience)


def generate_refresh_token() -> str:
    # URL-safe high entropy token
    return secrets.token_urlsafe(48)


def hash_refresh_token(refresh_token: str) -> str:
    # Pepper makes DB leaks less useful.
    data = (settings.refresh_token_pepper + refresh_token).encode("utf-8")
    return hashlib.sha256(data).hexdigest()
