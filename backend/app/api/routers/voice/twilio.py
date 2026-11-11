"""Twilio voice webhook: answers calls to a store's AI number.

Twilio POSTs here when someone calls (or a restaurant line forwards to) a
number we own. We reply with TwiML that either streams the call audio to the
voice agent (/voice/telephony/twilio/ws) or forwards it to the store's staff.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.core.phone import normalize_phone
from app.core.twilio import create_stream_token, is_valid_twilio_signature
from app.db.session import get_db
from app.models.store import Store

router = APIRouter(prefix="/voice/telephony/twilio", tags=["voice-telephony"])

_STREAM_PATH = "/voice/telephony/twilio/ws"
_SAY_ATTRS = {"voice": "Polly.Joanna", "language": "en-US"}
_DIAL_TIMEOUT_SECONDS = "25"


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


def _forward_to_staff(store: Store, caller: str | None) -> Response:
    root = ET.Element("Response")
    if store.phone_staff_number:
        # Show the customer's number to staff when we have it.
        attrs = {"timeout": _DIAL_TIMEOUT_SECONDS}
        if caller:
            attrs["callerId"] = caller
        ET.SubElement(root, "Dial", attrs).text = store.phone_staff_number
    else:
        _say(root, f"Thanks for calling {store.name}. Sorry, we can't take your call right now. Please try again later.")
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
    return _twiml(root)


@router.post("/incoming")
async def incoming_call(request: Request, db: Session = Depends(get_db)) -> Response:
    auth_token = settings.telephony_twilio_auth_token
    if not auth_token or not settings.telephony_twilio_account_sid or not settings.public_base_url:
        raise AppError(status_code=404, code="not_found", detail="Not found")

    form = await request.form()
    params = {key: str(value) for key, value in form.items()}
    # Twilio signs the public URL it called, not the address nginx proxies to.
    signed_url = _public_url(request.url.path, request.url.query)
    if not is_valid_twilio_signature(signed_url, params, request.headers.get("X-Twilio-Signature"), auth_token):
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
    return _connect_agent(store, call_sid=call_sid, caller=caller)
