"""Twilio helpers: webhook signature check and the short-lived media-stream token."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Mapping

from jose import JWTError, jwt

from app.core.config import settings

# Distinct audience so a stream token can never pass as an access token (and
# vice versa: access tokens carry mobile/web/admin audiences).
_STREAM_AUDIENCE = "twilio-media-stream"
# Twilio opens the media stream right after it reads our TwiML.
_STREAM_TOKEN_TTL_SECONDS = 60


def compute_twilio_signature(url: str, params: Mapping[str, str], auth_token: str) -> str:
    """Twilio's X-Twilio-Signature: base64(HMAC-SHA1(url + sorted key/value pairs))."""
    payload = url + "".join(f"{key}{params[key]}" for key in sorted(params))
    digest = hmac.new(auth_token.encode(), payload.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


def is_valid_twilio_signature(
    url: str, params: Mapping[str, str], signature: str | None, auth_token: str
) -> bool:
    if not signature:
        return False
    expected = compute_twilio_signature(url, params, auth_token)
    return hmac.compare_digest(expected.encode(), signature.encode())


@dataclass(frozen=True)
class StreamGrant:
    store_id: uuid.UUID
    call_sid: str
    caller: str | None


def create_stream_token(*, store_id: uuid.UUID, call_sid: str, caller: str | None) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(store_id),
        "aud": _STREAM_AUDIENCE,
        "call_sid": call_sid,
        "caller": caller,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=_STREAM_TOKEN_TTL_SECONDS)).timestamp()),
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_stream_token(token: str) -> StreamGrant:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm], audience=_STREAM_AUDIENCE
        )
        call_sid = payload["call_sid"]
        if not isinstance(call_sid, str) or not call_sid:
            raise ValueError("invalid stream token")
        caller = payload.get("caller")
        return StreamGrant(
            store_id=uuid.UUID(payload["sub"]),
            call_sid=call_sid,
            caller=caller if isinstance(caller, str) else None,
        )
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid stream token") from exc
