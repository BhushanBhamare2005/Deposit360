from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Deposit360"
    app_version: str = "0.1.0"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    secret_key: str = ""
    access_token_expire_minutes: int = Field(default=60, gt=0)
    cors_origins: str = "http://localhost:3000"
    database_url: str = "sqlite:///./deposit360.db"
    database_echo: bool = False
    storage_local_path: str = "./_storage"
    max_upload_size_mb: int = Field(default=20, gt=0)
    bank_verification_adapter: Literal["mock", "http"] = "mock"
    bank_verification_url: str = ""
    bank_verification_api_key: str = ""
    email_delivery_adapter: Literal["log", "http"] = "log"
    email_delivery_url: str = ""
    email_delivery_api_key: str = ""
    sms_delivery_adapter: Literal["log", "http"] = "log"
    sms_delivery_url: str = ""
    sms_delivery_api_key: str = ""
    lifecycle_scheduler_enabled: bool = True
    lifecycle_scheduler_interval_seconds: int = Field(default=3600, ge=60)
    maturity_reminder_interval_days: int = Field(default=1, ge=1)
    tesseract_cmd: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
