from __future__ import annotations

from fastapi import WebSocket

try:
    from pipecat.audio.vad.silero import SileroVADAnalyzer, VADParams
    from pipecat.transports.websocket.fastapi import (
        FastAPIWebsocketParams,
        FastAPIWebsocketTransport,
    )
    from pipecat.transports.base_transport import BaseTransport
except ImportError:  # pragma: no cover - optional dependency during Phase 2.3
    SileroVADAnalyzer = None
    VADParams = None
    FastAPIWebsocketParams = None
    FastAPIWebsocketTransport = None
    BaseTransport = object


def create_websocket_transport(websocket: WebSocket) -> BaseTransport:
    if FastAPIWebsocketTransport is None:
        raise RuntimeError("pipecat is required for websocket transport")

    vad_analyzer = SileroVADAnalyzer(
        params=VADParams(
            start_secs=0.2,
            stop_secs=0.8,
            min_volume=0.6,
        )
    )

    return FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=True,
            vad_enabled=True,
            vad_analyzer=vad_analyzer,
            vad_audio_passthrough=True,
        ),
    )
