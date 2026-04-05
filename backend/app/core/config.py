"""
Application configuration — all settings loaded from environment variables.
Never hardcode secrets here. Use .env for local dev.
"""

from enum import Enum
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


class AppEnvironment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    app_secret_key: str = "insecure-default-change-me"
    debug: bool = True
    app_name: str = "Stock Trading Platform"
    app_version: str = "0.1.0"

    # --- Database ---
    database_url: str = "postgresql+asyncpg://trader:changeme@postgres:5432/trading_platform"

    # --- Redis / Celery ---
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # --- Alpaca ---
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets"
    alpaca_data_url: str = "https://data.alpaca.markets"

    # --- Finnhub ---
    finnhub_api_key: str = ""

    # --- LLM (configurable) ---
    llm_provider: LLMProvider = LLMProvider.OLLAMA

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    # Ollama
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "llama3.1:8b"

    # --- JWT ---
    jwt_secret_key: str = "insecure-default-change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # --- Risk Management Defaults ---
    max_position_size_pct: float = 5.0
    max_portfolio_risk_pct: float = 20.0
    daily_loss_limit_pct: float = 3.0

    # --- CORS ---
    allowed_origins: str = "http://localhost:3000"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.app_env == AppEnvironment.PRODUCTION


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


# Convenience alias
settings = get_settings()
