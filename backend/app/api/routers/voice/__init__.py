from app.api.routers.voice.sessions import router as sessions_router
from app.api.routers.voice.orders import router as orders_router
from app.api.routers.voice.ws import router as ws_router
from app.api.routers.voice.telephony import router as telephony_router

"""Voice-related API endpoints, including telephony callbacks, WebSocket connections for real-time updates, 
and session management."""

__all__ = ["sessions_router", "orders_router", "ws_router", "telephony_router"]
