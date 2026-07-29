from __future__ import annotations

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

logger = logging.getLogger("voice.ws")

from app.api.host_policy import get_host_policy
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.session import get_db_session
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
from app.voice.usage import UsageAccumulator, estimate_monitor_cost

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
) -> None:
    """WebSocket endpoint for real-time voice interactions.
    Expects query parameters for store_id and optional order_id to establish context."""
    # Guard against missing PipelineRunner dependency (e.g. during Phase 2.3).
    if PipelineRunner is None:
        await websocket.close(code=1011)
        return

    # ── Setup phase: short-lived DB session for auth + config loading ──
    try:
        with get_db_session() as db:
            _require_user_host(websocket)
            current_user = _get_current_user_from_ws(websocket, db)
            current_user_id = current_user.id

            store = db.get(Store, store_id)
            store_name = store.name if store else None
            custom_prompt = None
            if store and store.custom_prompts:
                generated_parts = [
                    (p.get("generated") or "").strip()
                    for p in store.custom_prompts
                    if isinstance(p, dict) and (p.get("generated") or "").strip()
                ]
                if generated_parts:
                    custom_prompt = "\n\n".join(generated_parts)

            # Fulfillment context for the voice bot.
            store_address: str | None = None
            store_city: str | None = None
            store_state: str | None = None
            store_country: str | None = None
            allow_pickup_flag = True
            allow_delivery_flag = True
            if store is not None:
                allow_pickup_flag = bool(store.allow_pickup)
                allow_delivery_flag = bool(store.allow_delivery)
                addr_parts = [
                    (store.address_line1 or "").strip(),
                    (store.address_line2 or "").strip(),
                    (store.city or "").strip(),
                    (store.state or "").strip(),
                    (store.postal_code or "").strip(),
                ]
                joined = ", ".join(p for p in addr_parts if p)
                store_address = joined or None
                store_city = (store.city or "").strip() or None
                store_state = (store.state or "").strip() or None
                store_country = (store.country or "").strip() or None

            _VOICE_TONE_MAP = {
                "male": "Puck",
                "female": "Kore",
            }
            voice_id = _VOICE_TONE_MAP.get(store.voice_tone, "Puck") if store else "Puck"
            menu = load_menu_for_store(db, store_id)
        # db is now closed — connection returned to pool
    except AppError:
        await websocket.close(code=1008)
        return

    # ── Main phase: WebSocket accepted, pipeline running, long-lived connections to tools/LLMs ──
    await websocket.accept()

    runtime = load_voice_runtime_config()
    google_config = load_google_voice_config()
    system_prompt = build_system_prompt(
        menu_lines=menu,
        store_name=store_name,
        custom_prompt=custom_prompt,
        store_address=store_address,
        allow_pickup=allow_pickup_flag,
        allow_delivery=allow_delivery_flag,
        store_city=store_city,
        store_state=store_state,
        store_country=store_country,
    )

    # Tool context uses db_factory so each tool call gets its own short-lived session.
    tool_context = VoiceToolContext(
        db_factory=get_db_session,
        store_id=store_id,
        user_id=current_user_id,
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

    transport = create_websocket_transport(websocket)
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

    async def send_interruption() -> None:
        try:
            async with ws_send_lock:
                await websocket.send_text(json.dumps({"type": "interruption"}))
        except Exception:
            logger.debug("send_interruption failed", exc_info=True)

    tool_handlers = create_voice_tool_handlers(tool_context, monitor=monitor, on_order_update=send_order_update)

    usage = UsageAccumulator()

    task = create_voice_pipeline_task(
        transport=transport,
        runtime=runtime,
        google_config=google_config,
        system_prompt=system_prompt,
        tool_schema=GEMINI_VOICE_TOOLS_SCHEMA,
        tool_handlers=tool_handlers,
        on_transcript=send_transcript,
        on_interruption=send_interruption,
        monitor=monitor,
        usage=usage,
        voice_id=voice_id,
    )

    # Cancel pipeline when WebSocket disconnects so runner.run() returns promptly.
    @transport.event_handler("on_client_disconnected")
    async def _on_disconnect(transport_ref, ws):
        logger.info("Client disconnected, cancelling pipeline task")
        await task.cancel(reason="client_disconnected")

    runner = PipelineRunner()
    try:
        await runner.run(task)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: store=%s user=%s", store_id, current_user_id)
    except Exception:
        logger.exception("Pipeline error: store=%s user=%s", store_id, current_user_id)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        # Persist order_id and token usage with a fresh short-lived session.
        if session_id is not None:
            try:
                from app.models.voice_session import VoiceSession

                with get_db_session() as db:
                    vs = db.get(VoiceSession, session_id)
                    if vs is not None:
                        if tool_context.order_id is not None:
                            vs.order_id = tool_context.order_id
                        # Combine pipeline usage + monitor usage
                        total_prompt = usage.prompt_tokens + monitor.prompt_tokens
                        total_completion = usage.completion_tokens + monitor.completion_tokens
                        total_cost = usage.cost + estimate_monitor_cost(
                            monitor.prompt_tokens, monitor.completion_tokens
                        )
                        vs.prompt_tokens = total_prompt
                        vs.completion_tokens = total_completion
                        vs.total_tokens = total_prompt + total_completion
                        vs.llm_cost = total_cost
                        db.commit()
                        logger.warning(
                            "Session %s usage: pipeline=%d/%d, monitor=%d/%d, "
                            "total=%d prompt + %d completion = %d tokens, cost=$%s",
                            session_id,
                            usage.prompt_tokens, usage.completion_tokens,
                            monitor.prompt_tokens, monitor.completion_tokens,
                            total_prompt, total_completion,
                            total_prompt + total_completion, total_cost,
                        )
            except Exception:
                logger.exception("Failed to persist session data for %s", session_id)
