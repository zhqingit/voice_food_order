from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from app.core.config import settings
from app.core.errors import AppError
from app.schemas.common import Audience, PrincipalType


@dataclass(frozen=True)
class HostPolicy:
    principal: PrincipalType
    audience: Audience


def _split_hosts(value: str) -> set[str]:
    return {h.strip().lower() for h in value.split(",") if h.strip()}


def get_host_policy(request: Request) -> HostPolicy:
    host = (request.url.hostname or "").lower()
    user_hosts = _split_hosts(settings.user_api_hosts)
    store_hosts = _split_hosts(settings.store_api_hosts)

    if host in user_hosts:
        return HostPolicy(principal=PrincipalType.user, audience=Audience.mobile)
    if host in store_hosts:
        return HostPolicy(principal=PrincipalType.store, audience=Audience.web)

    raise AppError(status_code=403, code="invalid_host", detail="Invalid API host")


def require_host_policy(*, principal: PrincipalType, audience: Audience):
    def _dep(request: Request) -> HostPolicy:
        resolved = get_host_policy(request)
        if resolved.principal != principal or resolved.audience != audience:
            raise AppError(status_code=403, code="wrong_portal", detail="Wrong portal")
        return resolved

    return _dep
