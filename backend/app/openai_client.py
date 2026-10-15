"""OpenAI-compatible clients (official API or local LM Studio)."""

from __future__ import annotations

from openai import OpenAI

from app.config import get_settings


def chat_client() -> OpenAI:
    settings = get_settings()
    settings.require_openai()
    kwargs: dict = {
        "api_key": settings.openai_api_key,
        "timeout": settings.openai_timeout_seconds,
    }
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return OpenAI(**kwargs)


def embedding_client() -> OpenAI:
    """
    Embeddings can point at LM Studio while chat stays on OpenAI (or both local).
    OPENAI_EMBEDDING_BASE_URL wins; otherwise OPENAI_BASE_URL; otherwise api.openai.com.
    """
    settings = get_settings()
    settings.require_openai()
    kwargs: dict = {
        "api_key": settings.openai_api_key,
        "timeout": settings.openai_timeout_seconds,
    }
    base = settings.openai_embedding_base_url or settings.openai_base_url
    if base:
        kwargs["base_url"] = base
    return OpenAI(**kwargs)
