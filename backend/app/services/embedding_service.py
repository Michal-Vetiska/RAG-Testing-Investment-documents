"""Embedding generation via OpenAI-compatible API (OpenAI or LM Studio)."""

from __future__ import annotations

import logging

from app.config import get_settings
from app.openai_client import embedding_client

logger = logging.getLogger(__name__)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Convert texts into embedding vectors.
    An embedding is a fixed-length numeric vector that captures semantic meaning
    so similar texts land close together in vector space.
    """
    if not texts:
        return []

    settings = get_settings()
    settings.require_openai()
    client = embedding_client()
    model = settings.openai_embedding_model
    batch_size = settings.embedding_batch_size
    vectors: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(model=model, input=batch)
        ordered = sorted(response.data, key=lambda item: item.index)
        vectors.extend([item.embedding for item in ordered])
        logger.info(
            "Embedded batch %d–%d / %d (model=%s)",
            i + 1,
            i + len(batch),
            len(texts),
            model,
        )

    if len(vectors) != len(texts):
        raise RuntimeError("Embedding count does not match input text count")

    dim = len(vectors[0]) if vectors else 0
    if dim != settings.embedding_dimensions:
        raise RuntimeError(
            f"Embedding dimension {dim} does not match configured "
            f"{settings.embedding_dimensions}. Update the DB migration if you change models."
        )

    return vectors


def embed_query(question: str) -> list[float]:
    """Single-query helper used by retrieval."""
    return embed_texts([question])[0]
