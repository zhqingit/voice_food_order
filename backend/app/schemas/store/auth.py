from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class StoreSignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=2, max_length=255)
    phone: str | None = Field(default=None, max_length=32)


class StoreLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
