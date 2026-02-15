from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.user import get_current_user_mobile
from app.api.host_policy import require_host_policy
from app.core.errors import AppError
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Audience, PrincipalType
from app.schemas.voice.voice import VoiceSessionCreate, VoiceSessionOut
from app.services import voice_session_service

router = APIRouter(
    prefix="/voice/sessions",
    tags=["voice-sessions"],
    dependencies=[Depends(require_host_policy(principal=PrincipalType.user, audience=Audience.mobile))],
)


def _session_out(session) -> VoiceSessionOut:
    return VoiceSessionOut(
        id=session.id,
        store_id=session.store_id,
        user_id=session.user_id,
        channel=session.channel,
        status=session.status,
        started_at=session.started_at,
        ended_at=session.ended_at,
    )


@router.post("", response_model=VoiceSessionOut)
def create_session(
    payload: VoiceSessionCreate,
    current_user: User = Depends(get_current_user_mobile),
    db: Session = Depends(get_db),
) -> VoiceSessionOut:
    session = voice_session_service.create_session(
        db,
        store_id=payload.store_id,
        user_id=current_user.id,
        channel=payload.channel,
    )
    db.commit()
    db.refresh(session)
    return _session_out(session)


@router.post("/{session_id}/end", response_model=VoiceSessionOut)
def end_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user_mobile),
    db: Session = Depends(get_db),
) -> VoiceSessionOut:
    session = voice_session_service.get_session(db, session_id=session_id)
    if session is None or session.user_id != current_user.id:
        raise AppError(status_code=404, code="voice_session_not_found", detail="Voice session not found")

    voice_session_service.end_session(db, session=session)
    db.commit()
    db.refresh(session)
    return _session_out(session)
