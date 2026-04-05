"""
Configurable LLM provider factory.

Supports OpenAI, Anthropic, and Ollama (local).
Switch providers by setting LLM_PROVIDER in your .env — no code changes needed.
"""

from functools import lru_cache

from langchain_core.language_models import BaseChatModel
from loguru import logger

from app.core.config import LLMProvider, settings


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """
    Return a LangChain-compatible LLM instance based on the configured provider.
    Result is cached — same instance reused across agents.
    """
    provider = settings.llm_provider
    logger.info("Initializing LLM provider: {provider}", provider=provider)

    if provider == LLMProvider.OPENAI:
        from langchain_openai import ChatOpenAI
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.1,  # Low temp for more deterministic financial reasoning
        )

    elif provider == LLMProvider.ANTHROPIC:
        from langchain_anthropic import ChatAnthropic
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")
        return ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
            temperature=0.1,
        )

    elif provider == LLMProvider.OLLAMA:
        from langchain_ollama import ChatOllama
        logger.info(
            "Using Ollama at {url} with model {model}",
            url=settings.ollama_base_url,
            model=settings.ollama_model,
        )
        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.1,
        )

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def get_llm_info() -> dict:
    """Return metadata about the currently configured LLM."""
    provider = settings.llm_provider
    model_map = {
        LLMProvider.OPENAI: settings.openai_model,
        LLMProvider.ANTHROPIC: settings.anthropic_model,
        LLMProvider.OLLAMA: settings.ollama_model,
    }
    return {
        "provider": provider.value,
        "model": model_map.get(provider, "unknown"),
    }
