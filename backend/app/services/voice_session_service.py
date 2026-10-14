from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.time import utcnow_naive
from app.models.order import Order
from app.models.store import Store
from app.models.voice_session import VoiceSession


def get_orderable_store(db: Session, *, store_id: uuid.UUID) -> Store:
    """Return the store if customers can order from it, else raise 404/410."""
    store = db.get(Store, store_id)
    if store is None or not store.is_active:
        raise AppError(status_code=404, code="store_not_found", detail="Store not found")
    if not store.is_published:
        raise AppError(status_code=410, code="store_unpublished", detail="This store is no longer available")
    return store


def get_owned_session(
    db: Session, *, session_id: uuid.UUID, user_id: uuid.UUID, store_id: uuid.UUID
) -> VoiceSession:
    """Return an active voice session owned by *user_id* for *store_id*, else raise 404."""
    session = get_session(db, session_id=session_id)
    if (
        session is None
        or session.user_id != user_id
        or session.store_id != store_id
        or session.status != "active"
    ):
        raise AppError(status_code=404, code="voice_session_not_found", detail="Voice session not found")
    return session


def get_owned_draft_order(
    db: Session, *, order_id: uuid.UUID, user_id: uuid.UUID, store_id: uuid.UUID
) -> Order:
    """Return a draft order owned by *user_id* at *store_id*, else raise 404/409."""
    order = db.get(Order, order_id)
    if order is None or order.user_id != user_id or order.store_id != store_id:
        raise AppError(status_code=404, code="order_not_found", detail="Order not found")
    if order.status != "draft":
        raise AppError(status_code=409, code="order_not_editable", detail="Order is not editable")
    return order


def create_session(db: Session, *, store_id: uuid.UUID, user_id: uuid.UUID | None, channel: str) -> VoiceSession:
    session = VoiceSession(store_id=store_id, user_id=user_id, channel=channel, status="active")
    db.add(session)
    return session


def get_session(db: Session, *, session_id: uuid.UUID) -> VoiceSession | None:
    return db.execute(select(VoiceSession).where(VoiceSession.id == session_id)).scalar_one_or_none()


def end_session(db: Session, *, session: VoiceSession) -> VoiceSession:
    session.status = "ended"
    session.ended_at = utcnow_naive()
    return session
