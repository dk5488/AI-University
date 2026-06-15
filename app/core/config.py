from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI University"
    app_version: str = "0.1.0"
    environment: str = Field(default="local")
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg://ai_university:ai_university@localhost:5432/ai_university"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    openai_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
