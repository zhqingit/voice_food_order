from app.voice.transports.websocket import create_websocket_transport

try:
    from app.voice.transports.daily import create_daily_transport
except Exception:
    def create_daily_transport(**kwargs):  # type: ignore[misc]
        raise RuntimeError("Daily transport requires `pip install pipecat-ai[daily]`")

__all__ = ["create_websocket_transport", "create_daily_transport"]
