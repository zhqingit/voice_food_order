from __future__ import annotations

try:
    from pipecat.audio.vad.silero import SileroVADAnalyzer, VADParams
    from pipecat.transports.base_transport import BaseTransport
    from pipecat.transports.services.daily import DailyTransport, DailyTransportParams
except ImportError:  # pragma: no cover - optional dependency during Phase 2.4
    SileroVADAnalyzer = None
    VADParams = None
    DailyTransport = None
    DailyTransportParams = None
    BaseTransport = object


def create_daily_transport(*, room_url: str, token: str) -> BaseTransport:
    if DailyTransport is None:
        raise RuntimeError("pipecat is required for Daily transport")

    vad_analyzer = SileroVADAnalyzer(
        params=VADParams(
            start_secs=0.2,
            stop_secs=0.8,
            min_volume=0.6,
        )
    )

    return DailyTransport(
        room_url=room_url,
        token=token,
        bot_name="OrderBot",
        params=DailyTransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            camera_out_enabled=False,
            vad_enabled=True,
            vad_analyzer=vad_analyzer,
            vad_audio_passthrough=True,
        ),
    )
