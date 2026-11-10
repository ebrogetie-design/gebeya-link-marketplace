from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "production"
    app_name: str = "Gebeya Link Marketplace"
    bot_token: str
    telegram_webhook_secret: str = Field(min_length=16)
    public_base_url: str
    database_url: str
    admin_ids: str = ""
    support_username: str = ""
    currency: str = "ETB"
    default_country: str = "ET"
    max_upload_mb: int = 10
    upload_dir: str = "/var/data/uploads"
    log_level: str = "INFO"
    payment_provider: str = "manual"  # manual until provider credentials/webhooks are configured
    chapa_secret_key: str = ""
    chapa_webhook_secret: str = ""
    payment_callback_url: str = ""

    @property
    def admins(self) -> set[int]:
        return {int(x.strip()) for x in self.admin_ids.split(",") if x.strip().isdigit()}

    @property
    def webhook_url(self) -> str:
        return f"{self.public_base_url.rstrip('/')}/telegram/webhook"


@lru_cache
def get_settings() -> Settings:
    return Settings()
