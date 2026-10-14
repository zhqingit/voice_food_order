from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Values that must never reach a running server (old compose defaults etc.).
_PLACEHOLDER_SECRETS = {"change-me", "change-me-too", "changeme", "secret"}
_MIN_SECRET_LENGTH = 32


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

    # Required, no default: the app refuses to start without real secrets.
    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(48))"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 10

    refresh_token_ttl_days: int = 14
    refresh_token_pepper: str

    # Host-based API partitioning.
    # For local dev, you can map these hostnames to 127.0.0.1 via /etc/hosts.
    user_api_hosts: str = "user-api.local"
    store_api_hosts: str = "store-api.local"
    admin_api_hosts: str = "admin-api.local"

    # Multi-worker deployment
    web_workers: int = 4
    web_reload: bool = False

    cookie_secure: bool = False
    cookie_domain: str | None = None

    # Comma-separated explicit origins. Empty = no CORS (the store portal is
    # served same-origin behind nginx / the Vite proxy). "*" is rejected because
    # the store refresh cookie needs credentials.
    cors_origins: str = ""

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

    # Payments (Stripe Connect). Platform-level keys shared by all stores; each
    # store links its own Express account via Stripe-hosted onboarding and is
    # referenced by its acct_ id (stores.stripe_account_id).
    stripe_secret_key: str | None = None
    stripe_publishable_key: str | None = None
    # Webhook signing secret (whsec_...); set once the webhook is registered.
    stripe_webhook_secret: str | None = None
    # Platform commission in basis points (1000 = 10%). Default for all stores;
    # a store may override via stores.platform_fee_bps.
    platform_fee_bps: int = 1000

    @field_validator("jwt_secret", "refresh_token_pepper")
    @classmethod
    def _reject_weak_secret(cls, value: str, info) -> str:
        if value.strip().lower() in _PLACEHOLDER_SECRETS or len(value) < _MIN_SECRET_LENGTH:
            raise ValueError(
                f"{info.field_name.upper()} must be a random string of at least "
                f"{_MIN_SECRET_LENGTH} characters (not a placeholder)"
            )
        return value

    @field_validator("cors_origins")
    @classmethod
    def _reject_wildcard_origin(cls, value: str) -> str:
        if "*" in {o.strip() for o in value.split(",")}:
            raise ValueError("CORS_ORIGINS must list explicit origins; '*' is not allowed with credentials")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
