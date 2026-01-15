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


settings = Settings()
