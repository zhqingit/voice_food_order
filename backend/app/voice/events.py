from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import logging

from app.core.time import utcnow_naive

logger = logging.getLogger("voice.events")


class VoiceEventType(StrEnum):
    session_started = "session_started"
    session_ended = "session_ended"
    transcript_user = "transcript_user"
    transcript_bot = "transcript_bot"
    tool_call = "tool_call"
    tool_result = "tool_result"
    error = "error"


@dataclass(frozen=True)
class VoiceEvent:
    event_id: uuid.UUID
    session_id: uuid.UUID
    event_type: VoiceEventType
    payload: dict[str, object] | None
    created_at: datetime


def new_voice_event(
    *,
    session_id: uuid.UUID,
    event_type: VoiceEventType,
    payload: dict[str, object] | None = None,
) -> VoiceEvent:
    return VoiceEvent(
        event_id=uuid.uuid4(),
        session_id=session_id,
        event_type=event_type,
        payload=payload,
        created_at=utcnow_naive(),
    )


def log_voice_event(event: VoiceEvent) -> None:
    logger.info(
        "voice_event",
        extra={
            "event_id": str(event.event_id),
            "session_id": str(event.session_id),
            "event_type": event.event_type,
            "payload": event.payload or {},
            "created_at": event.created_at.isoformat(),
        },
    )
