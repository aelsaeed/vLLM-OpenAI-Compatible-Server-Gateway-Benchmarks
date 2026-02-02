from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gateway_host: str = "0.0.0.0"
    gateway_port: int = 8000
    vllm_base_url: str = "http://vllm:8000"
    model_id: str = "Qwen/Qwen2-0.5B-Instruct"

    redis_url: str = "redis://redis:6379/0"
    cache_ttl_seconds: int = 300

    rate_limit_rps: float = 5.0
    rate_limit_burst: int = 10
    request_size_limit_bytes: int = 1_000_000

    max_tokens_cap: int = 512
    denylist_words: list[str] = Field(default_factory=lambda: ["hack", "exploit"])

    retry_attempts: int = 3
    retry_min_seconds: float = 0.5
    retry_max_seconds: float = 3.0

    class Config:
        env_prefix = "GATEWAY_"


settings = Settings()
