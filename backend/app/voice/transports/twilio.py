from __future__ import annotations

from fastapi import WebSocket

from app.core.config import settings

try:
    from pipecat.serializers.twilio import TwilioFrameSerializer
    from pipecat.transports.base_transport import BaseTransport
    from pipecat.transports.websocket.fastapi import (
        FastAPIWebsocketParams,
        FastAPIWebsocketTransport,
    )
except ImportError:  # pragma: no cover - optional dependency
    TwilioFrameSerializer = None
    FastAPIWebsocketParams = None
    FastAPIWebsocketTransport = None
    BaseTransport = object


def create_twilio_transport(websocket: WebSocket, *, stream_sid: str, call_sid: str) -> BaseTransport:
    """Transport for a Twilio Media Stream (8 kHz mu-law, resampled by the serializer).

    When the pipeline ends the serializer hangs up the call through Twilio's
    REST API, so the caller isn't left on a silent line.
    """
    if FastAPIWebsocketTransport is None:
        raise RuntimeError("pipecat is required for the Twilio transport")

    serializer = TwilioFrameSerializer(
        stream_sid=stream_sid,
        call_sid=call_sid,
        account_sid=settings.telephony_twilio_account_sid,
        auth_token=settings.telephony_twilio_auth_token,
    )
    return FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            serializer=serializer,
        ),
    )
