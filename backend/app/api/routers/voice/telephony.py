from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.errors import AppError
from app.db.session import get_db_session
from app.models.user import User
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


@router.post("/daily/start")
async def start_daily_call(payload: DailyStartRequest) -> dict:
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
    )

    runner = PipelineRunner()
    asyncio.create_task(runner.run(task))
    return {"status": "starting"}
