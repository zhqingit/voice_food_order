from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class VoiceSessionCreate(BaseModel):
    store_id: uuid.UUID
    channel: str = Field(min_length=2, max_length=32)


class VoiceSessionOut(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    user_id: uuid.UUID | None
    channel: str
    status: str
    started_at: datetime
    ended_at: datetime | None


class VoiceEventIn(BaseModel):
    session_id: uuid.UUID
    event_type: str = Field(min_length=2, max_length=64)
    payload: dict[str, object] | None = None


class VoiceEventOut(BaseModel):
    session_id: uuid.UUID
    event_type: str
    payload: dict[str, object] | None = None
    created_at: datetime
