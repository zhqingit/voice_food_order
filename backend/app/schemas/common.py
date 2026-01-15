from __future__ import annotations

from enum import StrEnum


class PrincipalType(StrEnum):
    user = "user"
    store = "store"


class Audience(StrEnum):
    mobile = "mobile"
    web = "web"
