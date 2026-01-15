from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    session_id: uuid.UUID
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    session_id: uuid.UUID
    refresh_token: str


class LogoutRequest(BaseModel):
    scope: str = Field(pattern="^(current|all)$")
    session_id: uuid.UUID | None = None
