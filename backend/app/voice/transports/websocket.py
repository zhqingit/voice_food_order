from __future__ import annotations

from fastapi import WebSocket

try:
    from pipecat.audio.vad.silero import SileroVADAnalyzer, VADParams
    from pipecat.transports.websocket.fastapi import (
        FastAPIWebsocketParams,
        FastAPIWebsocketTransport,
    )
    from pipecat.transports.base_transport import BaseTransport
except ImportError:  # pragma: no cover - optional dependency
    SileroVADAnalyzer = None
    VADParams = None
    FastAPIWebsocketParams = None
    FastAPIWebsocketTransport = None
    BaseTransport = object

from app.voice.transports.raw_serializer import RawAudioSerializer


def create_websocket_transport(websocket: WebSocket) -> BaseTransport:
    if FastAPIWebsocketTransport is None:
        raise RuntimeError("pipecat is required for websocket transport")

    return FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            audio_out_sample_rate=24000,
            add_wav_header=False,
            serializer=RawAudioSerializer(sample_rate=16000, num_channels=1),
        ),
    )
