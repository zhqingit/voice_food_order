"""Per-store voice agent setup shared by the app WebSocket and phone calls."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.store import Store
from app.voice.menu import load_menu_for_store
from app.voice.monitor import ConversationMonitor, MonitorConfig
from app.voice.prompts import build_system_prompt

_VOICE_TONE_MAP = {
    "male": "Puck",
    "female": "Kore",
}


@dataclass(frozen=True)
class StoreVoiceSetup:
    system_prompt: str
    menu_text: str
    voice_id: str


def _custom_prompt(store: Store) -> str | None:
    parts = [
        (p.get("generated") or "").strip()
        for p in store.custom_prompts or []
        if isinstance(p, dict) and (p.get("generated") or "").strip()
    ]
    return "\n\n".join(parts) or None


def _clean(value: str | None) -> str | None:
    return (value or "").strip() or None


def load_store_voice_setup(db: Session, store: Store) -> StoreVoiceSetup:
    """Read everything the agent needs from the DB, so the session can close before the call runs."""
    menu = load_menu_for_store(db, store.id)
    addr_parts = [store.address_line1, store.address_line2, store.city, store.state, store.postal_code]
    store_address = ", ".join(p for p in (_clean(v) for v in addr_parts) if p) or None

    system_prompt = build_system_prompt(
        menu_lines=menu,
        store_name=store.name,
        custom_prompt=_custom_prompt(store),
        store_address=store_address,
        allow_pickup=bool(store.allow_pickup),
        allow_delivery=bool(store.allow_delivery),
        store_city=_clean(store.city),
        store_state=_clean(store.state),
        store_country=_clean(store.country),
    )
    return StoreVoiceSetup(
        system_prompt=system_prompt,
        menu_text="\n".join(menu) if menu else "",
        voice_id=_VOICE_TONE_MAP.get(store.voice_tone, "Puck"),
    )


def create_monitor(setup: StoreVoiceSetup) -> ConversationMonitor:
    return ConversationMonitor(
        menu_text=setup.menu_text,
        config=MonitorConfig(
            model=settings.voice_monitor_model,
            enabled=settings.voice_monitor_enabled,
        ),
    )
