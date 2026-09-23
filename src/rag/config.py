from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://rag:rag@127.0.0.1:5432/rag"
    rabbitmq_url: str = "amqp://rag:rag@127.0.0.1:5672/"
    qdrant_url: str = "http://127.0.0.1:6333"
    ollama_url: str = "http://127.0.0.1:11434"
    embedding_model: str = "qwen3-embedding:8b"
    qdrant_collection: str = "rag_chunks"
    search_max_candidates: int = Field(default=100, ge=1)
    rabbitmq_prefetch: int = Field(default=4, ge=1)
    rabbitmq_retry_delays: tuple[int, int, int] = (1, 5, 30)

    @field_validator("rabbitmq_retry_delays", mode="before")
    @classmethod
    def parse_retry_delays(cls, value: object) -> object:
        if isinstance(value, str):
            value = tuple(int(part.strip()) for part in value.split(","))
        if isinstance(value, (tuple, list)) and len(value) != 3:
            raise ValueError("RABBITMQ_RETRY_DELAYS must contain exactly three delays")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
