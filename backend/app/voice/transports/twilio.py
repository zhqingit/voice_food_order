from __future__ import annotations

from fastapi import WebSocket

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


def create_twilio_transport(websocket: WebSocket, *, stream_sid: str) -> BaseTransport:
    """Transport for a Twilio Media Stream (8 kHz mu-law, resampled by the serializer).

    No auto hang-up: when the stream closes, Twilio runs the TwiML after
    <Connect> (forward to staff, or say goodbye), which is how calls get
    transferred. Hanging up via the REST API would cut that off.
    """
    if FastAPIWebsocketTransport is None:
        raise RuntimeError("pipecat is required for the Twilio transport")

    serializer = TwilioFrameSerializer(
        stream_sid=stream_sid,
        params=TwilioFrameSerializer.InputParams(auto_hang_up=False),
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
