from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "auth-template-api"
    environment: str = "dev"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/auth_template"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 10

    refresh_token_ttl_days: int = 14
    refresh_token_pepper: str = "change-me-too"

    # Host-based API partitioning.
    # For local dev, you can map these hostnames to 127.0.0.1 via /etc/hosts.
    user_api_hosts: str = "user-api.local"
    store_api_hosts: str = "store-api.local"

    cookie_secure: bool = False
    cookie_domain: str | None = None

    cors_origins: str = "*"

    # Voice pipeline (provider + runtime limits)
    voice_provider_stt: str = "google"
    voice_provider_tts: str = "google"
    voice_provider_llm: str = "google"
    voice_llm_model: str = "gemini-3.0-flash-preview"

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
