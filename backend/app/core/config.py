from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "VoxEats API"
    environment: str = "dev"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/auth_template"

    # Database connection pool
    db_pool_size: int = 20
    db_max_overflow: int = 30
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 10

    refresh_token_ttl_days: int = 14
    refresh_token_pepper: str = "change-me-too"

    # Host-based API partitioning.
    # For local dev, you can map these hostnames to 127.0.0.1 via /etc/hosts.
    user_api_hosts: str = "user-api.local"
    store_api_hosts: str = "store-api.local"

    # Multi-worker deployment
    web_workers: int = 4
    web_reload: bool = False

    cookie_secure: bool = False
    cookie_domain: str | None = None

    cors_origins: str = "*"

    # Voice pipeline (provider + runtime limits)
    voice_provider_stt: str = "google"
    voice_provider_tts: str = "google"
    voice_provider_llm: str = "google"
    voice_llm_model: str = "gemini-3.1-flash-live-preview"
    # Live voice model when running on Vertex AI. GA native-audio model; the
    # `google/` prefix is required by pipecat's GeminiLiveVertexLLMService.
    voice_llm_model_vertex: str = "google/gemini-live-2.5-flash-native-audio"

    voice_monitor_model: str = "gemini-2.5-flash"
    voice_monitor_enabled: bool = True

    # Seconds the pipeline waits after the bot stops speaking before nudging
    # the LLM to ask a follow-up ("anything else?"). Longer = more patient bot.
    voice_silence_nudge_seconds: float = 8.0

    # Vertex AI (Gen AI). Two independent flags — the live voice pipeline and
    # the background text/image calls can pick different surfaces:
    #   * Background tasks: set GEMINI_USE_VERTEX=true for GA 2.5-flash
    #     reliability (prompt gen, image extract, note verify, monitor).
    #   * Live voice: set VOICE_USE_VERTEX=true to run GA 2.5-native-audio via
    #     Vertex (reliable but lower voice quality), or leave false to use the
    #     preview 3.1-flash-live on the Gemini API (better voice, occasional
    #     503s). Models for each surface are `voice_llm_model` /
    #     `voice_llm_model_vertex` below.
    gemini_use_vertex: bool = False
    voice_use_vertex: bool = False
    google_cloud_project: str = ""
    google_cloud_location: str = "us-central1"

    # Model IDs used by the non-realtime background tasks (note verify,
    # conversation monitor, menu image extract, custom prompt generator).
    # Vertex IDs carry the "google/" prefix; Gemini API IDs do not.
    gemini_background_model_vertex: str = "gemini-2.5-flash"
    gemini_background_model_api: str = "gemini-2.5-flash"

    voice_ws_max_seconds: int = 900
    voice_ws_max_payload_kb: int = 256
    voice_audio_sample_rate_hz: int = 16000

    # Telephony / WebRTC providers
    telephony_provider: str = "daily"
    telephony_daily_api_key: str | None = None
    telephony_daily_room_url: str | None = None

    telephony_twilio_account_sid: str | None = None
    telephony_twilio_auth_token: str | None = None
    telephony_twilio_app_sid: str | None = None


settings = Settings()
