from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.api.host_policy import get_host_policy
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Audience, PrincipalType
from app.voice import (
    GEMINI_VOICE_TOOLS_SCHEMA,
    VoiceToolContext,
    build_system_prompt,
    create_voice_pipeline_task,
    create_voice_tool_handlers,
    load_google_voice_config,
    load_voice_runtime_config,
)
from app.voice.transports.websocket import create_websocket_transport

try:
    from pipecat.pipeline.runner import PipelineRunner
except ImportError:  # pragma: no cover - optional dependency during Phase 2.3
    PipelineRunner = None

router = APIRouter(prefix="/voice", tags=["voice-ws"])


class _WebSocketRequest:
    def __init__(self, websocket: WebSocket):
        self.url = websocket.url


def _require_user_host(websocket: WebSocket) -> None:
    host = (websocket.url.hostname or "").lower()
    policy = get_host_policy(_WebSocketRequest(websocket))
    if policy.principal != PrincipalType.user or policy.audience != Audience.mobile:
        raise AppError(status_code=403, code="wrong_portal", detail="Wrong portal")
    if host == "":
        raise AppError(status_code=403, code="invalid_host", detail="Invalid API host")


def _get_current_user_from_ws(websocket: WebSocket, db: Session) -> User:
    auth = websocket.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        raise AppError(status_code=401, code="not_authenticated", detail="Not authenticated")
    token = auth.split(" ", 1)[1].strip()

    try:
        decoded = decode_access_token(token)
    except ValueError:
        raise AppError(status_code=401, code="invalid_access_token", detail="Invalid token")

    if decoded.role != PrincipalType.user or decoded.audience != Audience.mobile:
        raise AppError(status_code=403, code="wrong_portal", detail="Wrong portal")

    try:
        user_id = uuid.UUID(decoded.subject)
    except ValueError:
        raise AppError(status_code=401, code="invalid_access_token", detail="Invalid token")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AppError(status_code=401, code="invalid_access_token", detail="Invalid token")

    return user


@router.websocket("/ws")
async def voice_ws(
    websocket: WebSocket,
    store_id: uuid.UUID = Query(...),
    order_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
) -> None:
    if PipelineRunner is None:
        await websocket.close(code=1011)
        return

    try:
        _require_user_host(websocket)
        current_user = _get_current_user_from_ws(websocket, db)
    except AppError:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    runtime = load_voice_runtime_config()
    google_config = load_google_voice_config()
    system_prompt = build_system_prompt()

    tool_context = VoiceToolContext(
        db=db,
        store_id=store_id,
        user_id=current_user.id,
        order_id=order_id,
        channel="voice",
    )
    tool_handlers = create_voice_tool_handlers(tool_context)

    transport = create_websocket_transport(websocket)
    task = create_voice_pipeline_task(
        transport=transport,
        runtime=runtime,
        google_config=google_config,
        system_prompt=system_prompt,
        tool_schema=GEMINI_VOICE_TOOLS_SCHEMA,
        tool_handlers=tool_handlers,
    )

    runner = PipelineRunner()
    try:
        await runner.run(task)
    except WebSocketDisconnect:
        return
    except Exception:
        await websocket.close(code=1011)
        return
