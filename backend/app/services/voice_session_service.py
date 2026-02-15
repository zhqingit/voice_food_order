from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utcnow_naive
from app.models.voice_session import VoiceSession


def create_session(db: Session, *, store_id: uuid.UUID, user_id: uuid.UUID | None, channel: str) -> VoiceSession:
    session = VoiceSession(store_id=store_id, user_id=user_id, channel=channel, status="active")
    db.add(session)
    return session


def get_session(db: Session, *, session_id: uuid.UUID) -> VoiceSession | None:
    return db.execute(select(VoiceSession).where(VoiceSession.id == session_id)).scalar_one_or_none()


def end_session(db: Session, *, session: VoiceSession) -> VoiceSession:
    session.status = "ended"
    session.ended_at = utcnow_naive()
    return session
