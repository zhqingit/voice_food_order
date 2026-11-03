from __future__ import annotations

import asyncio
import hmac
import uuid

from fastapi import APIRouter, Header
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.errors import AppError
from app.db.session import get_db_session
from app.models.user import User
from app.services import voice_session_service
from app.voice import (
    GEMINI_VOICE_TOOLS_SCHEMA,
    VoiceToolContext,
    build_system_prompt,
    create_voice_pipeline_task,
    create_voice_tool_handlers,
    load_google_voice_config,
    load_voice_runtime_config,
)
from app.voice.transports.daily import create_daily_transport

try:
    from pipecat.pipeline.runner import PipelineRunner
except ImportError:  # pragma: no cover - optional dependency during Phase 2.4
    PipelineRunner = None

router = APIRouter(prefix="/voice/telephony", tags=["voice-telephony"])


class DailyStartRequest(BaseModel):
    room_url: str = Field(min_length=8)
    token: str = Field(min_length=8)
    store_id: uuid.UUID
    order_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None


def _require_telephony_secret(provided: str | None) -> None:
    expected = settings.telephony_shared_secret
    if not expected:
        raise AppError(status_code=404, code="not_found", detail="Not found")
    if provided is None or not hmac.compare_digest(provided.encode(), expected.encode()):
        raise AppError(status_code=401, code="invalid_telephony_secret", detail="Invalid telephony secret")


@router.post("/daily/start")
async def start_daily_call(
    payload: DailyStartRequest,
    x_telephony_secret: str | None = Header(default=None),
) -> dict:
    _require_telephony_secret(x_telephony_secret)
    if PipelineRunner is None:
        raise AppError(status_code=501, code="voice_unavailable", detail="Voice pipeline not available")

    # Short-lived session for setup queries only.
    user_id: uuid.UUID | None = None
    with get_db_session() as db:
        if payload.user_id is not None:
            user: User | None = db.get(User, payload.user_id)
            if user is None or not user.is_active:
                raise AppError(status_code=404, code="user_not_found", detail="User not found")
            user_id = user.id
        voice_session_service.get_orderable_store(db, store_id=payload.store_id)
        if payload.order_id is not None:
            voice_session_service.get_owned_draft_order(
                db, order_id=payload.order_id, user_id=user_id, store_id=payload.store_id
            )

    runtime = load_voice_runtime_config()
    google_config = load_google_voice_config()
    system_prompt = build_system_prompt()

    tool_context = VoiceToolContext(
        db_factory=get_db_session,
        store_id=payload.store_id,
        user_id=user_id,
        order_id=payload.order_id,
        channel="phone",
    )
    tool_handlers = create_voice_tool_handlers(tool_context)

    transport = create_daily_transport(room_url=payload.room_url, token=payload.token)
    task = create_voice_pipeline_task(
        transport=transport,
        runtime=runtime,
        google_config=google_config,
        system_prompt=system_prompt,
        tool_schema=GEMINI_VOICE_TOOLS_SCHEMA,
        tool_handlers=tool_handlers,
        on_bot_stopped_speaking=tool_context.mark_bot_stopped_speaking,
    )

    runner = PipelineRunner()
    asyncio.create_task(runner.run(task))
    return {"status": "starting"}
