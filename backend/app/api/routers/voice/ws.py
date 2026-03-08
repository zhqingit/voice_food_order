from __future__ import annotations

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

logger = logging.getLogger("voice.ws")

from app.api.host_policy import get_host_policy
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.store import Store
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
from app.voice.menu import load_menu_for_store
from app.core.config import settings
from app.voice.monitor import ConversationMonitor, MonitorConfig
from app.voice.transports.websocket import create_websocket_transport

try:
    from pipecat.pipeline.runner import PipelineRunner
except ImportError:  # pragma: no cover - optional dependency during Phase 2.3
    PipelineRunner = None

router = APIRouter(prefix="/voice", tags=["voice-ws"])


class _HostURL:
    """Expose Host-header hostname so get_host_policy works for WebSockets."""

    def __init__(self, hostname: str):
        self.hostname = hostname


class _WebSocketRequest:
    def __init__(self, websocket: WebSocket):
        raw_host = (websocket.headers.get("host") or "").lower()
        # Strip port if present (e.g. "user-api.local:8000" → "user-api.local")
        self.url = _HostURL(raw_host.split(":")[0])


def _require_user_host(websocket: WebSocket) -> None:
    host = _WebSocketRequest(websocket).url.hostname
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
    session_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
) -> None:
    """WebSocket endpoint for real-time voice interactions. 
    Expects query parameters for store_id and optional order_id to establish context."""
    if PipelineRunner is None:
        await websocket.close(code=1011)
        return

    # Validate host and authenticate user using the same logic as HTTP endpoints, but adapted for WebSocket headers.
    try:
        _require_user_host(websocket)
        current_user = _get_current_user_from_ws(websocket, db)
    except AppError:
        await websocket.close(code=1008)
        return

    # Accept the WebSocket connection after successful authentication. 
    # From this point on, we can send/receive messages.
    await websocket.accept()

    # Load voice runtime config, system prompt, 
    # and initialize tool handlers with the current context (store_id, user_id, order_id).
    store = db.get(Store, store_id)
    store_name = store.name if store else None

    # Map store voice tone preference to Gemini voice ID
    _VOICE_TONE_MAP = {
        "male": "Puck",
        "female": "Kore",
    }
    voice_id = _VOICE_TONE_MAP.get(store.voice_tone, "Puck") if store else "Puck"
    menu = load_menu_for_store(db, store_id)
    runtime = load_voice_runtime_config()
    google_config = load_google_voice_config()
    system_prompt = build_system_prompt(menu_lines=menu, store_name=store_name)

    # The tool context provides necessary information for the tool handlers to operate,
    # such as database access and user/store/order context.
    tool_context = VoiceToolContext(
        db=db,
        store_id=store_id,
        user_id=current_user.id,
        order_id=order_id,
        session_id=session_id,
        channel="voice",
    )

    # Create the async conversation monitor (Gemini Pro checks each bot turn).
    menu_text = "\n".join(menu) if menu else ""
    monitor = ConversationMonitor(
        menu_text=menu_text,
        config=MonitorConfig(
            model=settings.voice_monitor_model,
            enabled=settings.voice_monitor_enabled,
        ),
    )

    # Create a WebSocket transport that the voice pipeline can use to send/receive messages,
    # and run the pipeline in a background task.
    transport = create_websocket_transport(websocket)
    # TODO: We may want to implement some form of cancellation or timeout handling, 
    # especially for long-running pipelines, to avoid orphaned tasks if the client disconnects.
    # Lock to prevent concurrent WebSocket text sends (pipecat transport
    # may be sending binary audio at the same time).
    ws_send_lock = asyncio.Lock()

    async def send_transcript(role: str, content: str) -> None:
        try:
            async with ws_send_lock:
                await websocket.send_text(
                    json.dumps({"type": f"transcript_{role}", "text": content})
                )
        except Exception:
            logger.debug("send_transcript failed for role=%s", role, exc_info=True)

    async def send_order_update(order: dict) -> None:
        try:
            async with ws_send_lock:
                await websocket.send_text(
                    json.dumps({"type": "order_update", "order": order})
                )
        except Exception:
            logger.debug("send_order_update failed", exc_info=True)

    tool_handlers = create_voice_tool_handlers(tool_context, monitor=monitor, on_order_update=send_order_update)

    task = create_voice_pipeline_task(
        transport=transport,
        runtime=runtime,
        google_config=google_config,
        system_prompt=system_prompt,
        tool_schema=GEMINI_VOICE_TOOLS_SCHEMA,
        tool_handlers=tool_handlers,
        on_transcript=send_transcript,
        monitor=monitor,
        voice_id=voice_id,
    )

    runner = PipelineRunner()
    try:
        await runner.run(task)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: store=%s user=%s", store_id, current_user.id)
    except Exception:
        logger.exception("Pipeline error: store=%s user=%s", store_id, current_user.id)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        # Persist the order_id created during the pipeline back to the voice session.
        if session_id is not None and tool_context.order_id is not None:
            try:
                from app.models.voice_session import VoiceSession

                vs = db.get(VoiceSession, session_id)
                if vs is not None:
                    vs.order_id = tool_context.order_id
                    db.commit()
            except Exception:
                logger.exception("Failed to persist order_id to session %s", session_id)
