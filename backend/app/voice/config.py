from __future__ import annotations

import os
from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True)
class VoiceRuntimeConfig:
    stt_provider: str
    tts_provider: str
    llm_provider: str
    llm_model: str
    audio_sample_rate_hz: int
    ws_max_seconds: int
    ws_max_payload_kb: int


@dataclass(frozen=True)
class GoogleVoiceConfig:
    api_key: str
    credentials_path: str


def load_voice_runtime_config() -> VoiceRuntimeConfig:
    return VoiceRuntimeConfig(
        stt_provider=settings.voice_provider_stt,
        tts_provider=settings.voice_provider_tts,
        llm_provider=settings.voice_provider_llm,
        llm_model=settings.voice_llm_model,
        audio_sample_rate_hz=settings.voice_audio_sample_rate_hz,
        ws_max_seconds=settings.voice_ws_max_seconds,
        ws_max_payload_kb=settings.voice_ws_max_payload_kb,
    )


def load_google_voice_config() -> GoogleVoiceConfig:
    api_key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
    credentials_path = (os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "").strip()
    return GoogleVoiceConfig(api_key=api_key, credentials_path=credentials_path)
