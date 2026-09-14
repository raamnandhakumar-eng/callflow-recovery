from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    demo_mode: bool = True
    database_url: str = "sqlite:///./callflow.db"
    public_base_url: str = "http://localhost:8000"
    default_tenant_slug: str = "northstar-hvac"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_input_cost_per_million: float = 0.40
    openai_output_cost_per_million: float = 1.60

    hubspot_access_token: str | None = None

    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_number: str | None = None

    vapi_webhook_secret: str | None = None

    http_timeout_seconds: float = 8.0
    max_external_retries: int = 2


@lru_cache
def get_settings() -> Settings:
    return Settings()
