from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.user.auth import router as user_auth_router
from app.api.routers.user.me import router as user_router
from app.api.routers.user.orders import router as user_orders_router
from app.api.routers.store.auth import router as store_auth_router
from app.api.routers.store.me import router as store_router
from app.api.routers.store.menu import router as store_menu_router
from app.api.routers.store.orders import router as store_orders_router
from app.api.routers.voice.sessions import router as voice_sessions_router
from app.api.routers.voice.orders import router as voice_orders_router
from app.api.routers.voice.ws import router as voice_ws_router
from app.api.routers.voice.telephony import router as voice_telephony_router
from app.core.config import settings
from app.core.errors import AppError, app_error_handler

app = FastAPI(title=settings.app_name)

app.add_exception_handler(AppError, app_error_handler)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(user_auth_router)
app.include_router(user_router)
app.include_router(user_orders_router)
app.include_router(store_auth_router)
app.include_router(store_router)
app.include_router(store_menu_router)
app.include_router(store_orders_router)
app.include_router(voice_sessions_router)
app.include_router(voice_orders_router)
app.include_router(voice_ws_router)
app.include_router(voice_telephony_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
