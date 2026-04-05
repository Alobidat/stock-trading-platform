"""Tests for application configuration."""

import pytest
from app.core.config import LLMProvider, Settings


def test_default_llm_provider():
    """Default LLM provider should be ollama."""
    settings = Settings()
    assert settings.llm_provider == LLMProvider.OLLAMA


def test_allowed_origins_list():
    """allowed_origins_list should split comma-separated string."""
    settings = Settings(allowed_origins="http://localhost:3000,http://localhost:3001")
    origins = settings.allowed_origins_list
    assert "http://localhost:3000" in origins
    assert "http://localhost:3001" in origins


def test_llm_provider_enum_values():
    """Verify all expected LLM providers are available."""
    assert LLMProvider.OPENAI == "openai"
    assert LLMProvider.ANTHROPIC == "anthropic"
    assert LLMProvider.OLLAMA == "ollama"


def test_risk_defaults():
    """Risk management defaults should be sensible."""
    settings = Settings()
    assert 0 < settings.max_position_size_pct <= 10
    assert 0 < settings.daily_loss_limit_pct <= 10
