from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

SETTINGS_CONFIG = SettingsConfigDict(env_file=".env", env_prefix="BOOKREC_", extra="ignore")


class LoggingSettings(BaseSettings):
    model_config = SETTINGS_CONFIG

    log_level: str = "INFO"
    log_json: bool = True


class Settings(LoggingSettings):
    database_dsn: str
    health_check_timeout: float = 2.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
