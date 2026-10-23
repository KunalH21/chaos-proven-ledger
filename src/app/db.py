from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql+asyncpg://ledger:ledger@localhost:5432/ledger_db"
    FAULTS_ENABLED: bool = False
    FAULT_RATE: float = 0.3


settings = Settings()
