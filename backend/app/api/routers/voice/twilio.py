"""Twilio phone line: answers calls to a store's AI number.

1. Twilio POSTs /incoming when someone calls (or a restaurant line forwards
   to) a number we own. We reply with TwiML that either streams the call audio
   to the voice agent, forwards it to the store's staff, or says the store is
   closed.
2. For the agent, Twilio opens the /ws media stream and we run the same voice
   pipeline as the app, with 8 kHz telephone audio.
3. When the stream closes while the caller is still on the line (they asked
   for a person or pressed 0, or the call hit its time limit), Twilio carries
   on with the TwiML after <Connect>: ring the staff, or say goodbye.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import xml.etree.ElementTree as ET

from fastapi import APIRouter, Depends, Request, Response, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.core.phone import normalize_phone
from app.core.twilio import StreamGrant, create_stream_token, decode_stream_token, is_valid_twilio_signature
from app.db.session import get_db, get_db_session
from app.models.store import Store
from app.services import voice_session_service
from app.services.store_hours_service import store_open_status
from app.voice import (
    VoiceToolContext,
    create_voice_pipeline_task,
    create_voice_tool_handlers,
    load_google_voice_config,
    load_voice_runtime_config,
)
from app.voice.prompts import PhoneCallInfo, phone_greeting
from app.voice.session_setup import create_monitor, load_store_voice_setup
from app.voice.tools import build_voice_tools_schema
from app.voice.transports.twilio import create_twilio_transport
from app.voice.usage import UsageAccumulator, estimate_monitor_cost

try:
    from pipecat.pipeline.runner import PipelineRunner
except ImportError:  # pragma: no cover - optional dependency
    PipelineRunner = None

logger = logging.getLogger("voice.twilio")

router = APIRouter(prefix="/voice/telephony/twilio", tags=["voice-telephony"])

_STREAM_PATH = "/voice/telephony/twilio/ws"
_SAY_ATTRS = {"voice": "Polly.Joanna", "language": "en-US"}
_DIAL_TIMEOUT_SECONDS = "25"
# Twilio sends "connected" then "start" right after the socket opens.
_START_TIMEOUT_SECONDS = 10
# Longest we wait for the bot's "connecting you now" line before transferring.
_TRANSFER_LINE_TIMEOUT_SECONDS = 10
_TRANSFER_KEY = "0"


def _twilio_configured() -> bool:
    return bool(
        settings.telephony_twilio_auth_token
        and settings.telephony_twilio_account_sid
        and settings.public_base_url
    )


def _public_url(path: str, query: str = "") -> str:
    url = settings.public_base_url.rstrip("/") + path
    return f"{url}?{query}" if query else url


def _twiml(response: ET.Element) -> Response:
    body = '<?xml version="1.0" encoding="UTF-8"?>' + ET.tostring(response, encoding="unicode")
    return Response(content=body, media_type="application/xml")


def _say(parent: ET.Element, text: str) -> None:
    ET.SubElement(parent, "Say", _SAY_ATTRS).text = text


def _safe_phone(value: str | None) -> str | None:
    try:
        return normalize_phone(value or "")
    except ValueError:
        return None  # withheld / anonymous caller IDs


def _not_in_service() -> Response:
    root = ET.Element("Response")
    _say(root, "Sorry, this number is not in service.")
    ET.SubElement(root, "Hangup")
    return _twiml(root)


def _staff_or_goodbye(root: ET.Element, store: Store, caller: str | None, goodbye: str) -> None:
    if store.phone_staff_number:
        # Show the customer's number to staff when we have it.
        attrs = {"timeout": _DIAL_TIMEOUT_SECONDS}
        if caller:
            attrs["callerId"] = caller
        ET.SubElement(root, "Dial", attrs).text = store.phone_staff_number
    else:
        _say(root, goodbye)
        ET.SubElement(root, "Hangup")


def _forward_to_staff(store: Store, caller: str | None) -> Response:
    root = ET.Element("Response")
    _staff_or_goodbye(
        root, store, caller,
        f"Thanks for calling {store.name}. Sorry, we can't take your call right now. Please try again later.",
    )
    return _twiml(root)


def _closed(store: Store, today_text: str | None) -> Response:
    root = ET.Element("Response")
    hours = "We're closed today." if today_text in (None, "closed") else f"Today's hours are {today_text}."
    _say(root, f"Thanks for calling {store.name}. We're closed right now. {hours} Please call back when we're open.")
    ET.SubElement(root, "Hangup")
    return _twiml(root)


def _connect_agent(store: Store, *, call_sid: str, caller: str | None) -> Response:
    token = create_stream_token(store_id=store.id, call_sid=call_sid, caller=caller)
    ws_url = _public_url(_STREAM_PATH).replace("https://", "wss://", 1).replace("http://", "ws://", 1)
    root = ET.Element("Response")
    connect = ET.SubElement(root, "Connect")
    # Twilio drops query strings on Stream URLs; custom data rides in <Parameter>
    # and arrives in the stream's "start" message.
    stream = ET.SubElement(connect, "Stream", {"url": ws_url})
    ET.SubElement(stream, "Parameter", {"name": "token", "value": token})
    # Runs only if we close the stream with the caller still on the line.
    _staff_or_goodbye(
        root, store, caller, "Sorry, we have to end the call now. Please call back if you need anything. Goodbye."
    )
    return _twiml(root)


@router.post("/incoming")
async def incoming_call(request: Request, db: Session = Depends(get_db)) -> Response:
    if not _twilio_configured():
        raise AppError(status_code=404, code="not_found", detail="Not found")

    form = await request.form()
    params = {key: str(value) for key, value in form.items()}
    # Twilio signs the public URL it called, not the address nginx proxies to.
    signed_url = _public_url(request.url.path, request.url.query)
    if not is_valid_twilio_signature(
        signed_url, params, request.headers.get("X-Twilio-Signature"), settings.telephony_twilio_auth_token
    ):
        raise AppError(status_code=403, code="invalid_signature", detail="Invalid signature")

    if params.get("AccountSid") != settings.telephony_twilio_account_sid:
        raise AppError(status_code=403, code="invalid_account", detail="Invalid account")

    to_number = _safe_phone(params.get("To"))
    call_sid = params.get("CallSid", "")
    caller = _safe_phone(params.get("From"))

    store = None
    if to_number:
        store = db.execute(select(Store).where(Store.phone_ai_number == to_number)).scalar_one_or_none()
    if store is None or not store.is_active:
        return _not_in_service()

    agent_ready = store.phone_ai_enabled and store.is_approved and store.is_published and call_sid
    if not agent_ready:
        return _forward_to_staff(store, caller)
    hours = store_open_status(db, store)
    if hours.is_open is False:
        return _closed(store, hours.today_text)
    return _connect_agent(store, call_sid=call_sid, caller=caller)


async def _read_stream_start(websocket: WebSocket) -> dict:
    """Return the media stream's "start" payload (skipping "connected")."""
    while True:
        message = json.loads(await websocket.receive_text())
        event = message.get("event")
        if event == "start":
            return message.get("start") or {}
        if event != "connected":
            raise ValueError(f"unexpected Twilio event before start: {event}")


def _authorize_stream(start: dict) -> StreamGrant:
    token = (start.get("customParameters") or {}).get("token") or ""
    grant = decode_stream_token(token)
    # The token was minted for this exact call; refuse it on any other stream.
    if grant.call_sid != start.get("callSid") or not start.get("streamSid"):
        raise ValueError("stream does not match token")
    return grant


@router.websocket("/ws")
async def media_stream(websocket: WebSocket) -> None:
    if PipelineRunner is None or not _twilio_configured():
        await websocket.close(code=1011)
        return

    # Twilio only sends the call details (and our token) after the socket is open.
    await websocket.accept()
    try:
        start = await asyncio.wait_for(_read_stream_start(websocket), timeout=_START_TIMEOUT_SECONDS)
        grant = _authorize_stream(start)
        with get_db_session() as db:
            store = voice_session_service.get_orderable_store(db, store_id=grant.store_id)
            if not store.phone_ai_enabled:
                raise AppError(status_code=409, code="phone_ai_disabled", detail="Phone ordering is off")
            phone = PhoneCallInfo(caller_known=grant.caller is not None, can_transfer=bool(store.phone_staff_number))
            setup = load_store_voice_setup(db, store, phone=phone)
            greeting = phone_greeting(store.name)
    except (AppError, ValueError, TimeoutError, WebSocketDisconnect) as exc:
        logger.warning("Rejected Twilio media stream: %s", exc)
        await websocket.close(code=1008)
        return

    store_id = grant.store_id
    call_sid = grant.call_sid
    runtime = load_voice_runtime_config()
    tool_context = VoiceToolContext(
        db_factory=get_db_session,
        store_id=store_id,
        user_id=None,
        channel="phone",
        customer_phone=grant.caller,
    )
    # Transfer to staff: the bot says its line, then we close the stream and
    # Twilio dials the staff number from the TwiML after <Connect>.
    transfer = asyncio.Event()
    transfer_immediately = False
    transfer_asked_at = 0.0

    def _request_transfer(*, immediately: bool = False) -> None:
        nonlocal transfer_immediately, transfer_asked_at
        if not phone.can_transfer or transfer.is_set():
            return
        transfer_immediately = immediately
        transfer_asked_at = time.monotonic()
        transfer.set()

    def _on_keypad(digit: str) -> None:
        if digit == _TRANSFER_KEY:
            _request_transfer(immediately=True)

    monitor = create_monitor(setup)
    tool_handlers = create_voice_tool_handlers(
        tool_context, monitor=monitor, on_transfer_requested=_request_transfer
    )
    usage = UsageAccumulator()

    try:
        transport = create_twilio_transport(websocket, stream_sid=start["streamSid"])
        task = create_voice_pipeline_task(
            transport=transport,
            runtime=runtime,
            google_config=load_google_voice_config(),
            system_prompt=setup.system_prompt,
            tool_schema=build_voice_tools_schema(phone=True, can_transfer=phone.can_transfer),
            tool_handlers=tool_handlers,
            on_bot_started_speaking=tool_context.mark_bot_started_speaking,
            on_bot_stopped_speaking=tool_context.mark_bot_stopped_speaking,
            on_customer_said=tool_context.mark_customer_said,
            monitor=monitor,
            usage=usage,
            voice_id=setup.voice_id,
            greeting=greeting,
            on_dtmf=_on_keypad,
        )
    except Exception:
        logger.exception("Failed to start phone pipeline: store=%s call=%s", store_id, call_sid)
        await websocket.close(code=1011)
        return

    @transport.event_handler("on_client_disconnected")
    async def _on_disconnect(transport_ref, ws):
        await task.cancel(reason="caller_hung_up")

    async def _enforce_max_duration() -> None:
        await asyncio.sleep(runtime.ws_max_seconds)
        logger.info("Phone call hit %ss limit: store=%s call=%s", runtime.ws_max_seconds, store_id, call_sid)
        await task.cancel(reason="max_duration")  # Twilio then hands the caller to staff

    async def _transfer_when_ready() -> None:
        await transfer.wait()
        if not transfer_immediately:
            # Let the bot finish "connecting you now" before the line switches.
            deadline = transfer_asked_at + _TRANSFER_LINE_TIMEOUT_SECONDS
            while time.monotonic() < deadline:
                ended = tool_context.bot_speech_ended_at
                if not tool_context.bot_speaking and ended is not None and ended > transfer_asked_at:
                    break
                await asyncio.sleep(0.2)
        logger.info("Transferring phone call to staff: store=%s call=%s", store_id, call_sid)
        await task.cancel(reason="transfer_to_staff")

    logger.info("Phone call started: store=%s call=%s", store_id, call_sid)
    watchdog = asyncio.create_task(_enforce_max_duration())
    transfer_watch = asyncio.create_task(_transfer_when_ready())
    try:
        await PipelineRunner().run(task)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Phone pipeline error: store=%s call=%s", store_id, call_sid)
    finally:
        watchdog.cancel()
        transfer_watch.cancel()
        # Closing the stream is what moves Twilio on to the TwiML after <Connect>.
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.close()
            except Exception:
                pass
        prompt = usage.prompt_tokens + monitor.prompt_tokens
        completion = usage.completion_tokens + monitor.completion_tokens
        cost = usage.cost + estimate_monitor_cost(monitor.prompt_tokens, monitor.completion_tokens)
        logger.warning(
            "Phone call ended: store=%s call=%s order=%s tokens=%d/%d cost=$%s",
            store_id, call_sid, tool_context.order_id, prompt, completion, cost,
        )
