from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "orderflow-demo"
    environment: str = "local"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./orderflow_demo.db"
    threadline_db: str = "postgresql+psycopg://threadline:threadline_dev_password@localhost:5433/threadline_db"
    downstream_base_url: str = "http://downstream.local"
    threadline_sidecar_url: str = "http://localhost:4949"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
