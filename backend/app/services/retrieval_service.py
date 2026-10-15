"""
Vector retrieval only — never calls the chat LLM.

This separation lets us debug whether a bad answer came from
missing/wrong chunks (retrieval) or misuse of good context (generation).
"""

from __future__ import annotations

import logging
import time
from typing import Any

from app.config import get_settings
from app.database import get_supabase
from app.models.domain import RetrievedChunk
from app.services.document_service import list_display_names
from app.services.embedding_service import embed_query

logger = logging.getLogger(__name__)


def _mentioned_documents(question: str, display_names: list[str]) -> list[str]:
    """Find fund display names explicitly mentioned in the question (case-insensitive)."""
    q = question.lower()
    found: list[str] = []
    # Prefer longer names first to avoid partial overlaps.
    for name in sorted(display_names, key=len, reverse=True):
        if name.lower() in q:
            found.append(name)
    return found


def _balance_by_documents(
    chunks: list[RetrievedChunk],
    mentioned: list[str],
    top_k: int,
) -> list[RetrievedChunk]:
    """
    When the question names multiple documents, reserve slots so one fund
    does not crowd out the other. Still preference-ordered by similarity.
    """
    if len(mentioned) < 2:
        return chunks[:top_k]

    per_doc = max(1, top_k // len(mentioned))
    selected: list[RetrievedChunk] = []
    used_ids: set[str] = set()

    for name in mentioned:
        group = [c for c in chunks if c.document == name and c.chunk_id not in used_ids]
        for chunk in group[:per_doc]:
            selected.append(chunk)
            used_ids.add(chunk.chunk_id)

    # Fill remaining slots with highest-similarity leftovers.
    for chunk in chunks:
        if len(selected) >= top_k:
            break
        if chunk.chunk_id not in used_ids:
            selected.append(chunk)
            used_ids.add(chunk.chunk_id)

    selected.sort(key=lambda c: c.similarity, reverse=True)
    return selected[:top_k]


def retrieve(question: str) -> tuple[list[RetrievedChunk], int]:
    """
    1. Embed the question
    2. Call match_document_chunks RPC (pgvector cosine search)
    3. Apply TOP_K / multi-doc balancing
    4. Return chunks already filtered by similarity threshold in SQL
    """
    settings = get_settings()
    settings.require_openai()
    settings.require_supabase()

    started = time.perf_counter()
    query_embedding = embed_query(question)

    display_names = list_display_names()
    mentioned = _mentioned_documents(question, display_names)

    # Pull a wider candidate set when multiple funds are named.
    match_count = settings.rag_top_k
    if len(mentioned) >= 2:
        match_count = settings.rag_top_k * len(mentioned)

    client = get_supabase()
    result = client.rpc(
        "match_document_chunks",
        {
            "query_embedding": query_embedding,
            "match_threshold": settings.rag_similarity_threshold,
            "match_count": match_count,
        },
    ).execute()

    rows: list[dict[str, Any]] = result.data or []
    chunks = [
        RetrievedChunk(
            chunk_id=str(row["chunk_id"]),
            document_id=str(row["document_id"]),
            document=row["display_name"],
            filename=row["filename"],
            page=int(row["page_number"]),
            content=row["content"],
            similarity=float(row["similarity"]),
        )
        for row in rows
    ]

    chunks = _balance_by_documents(chunks, mentioned, settings.rag_top_k)
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    logger.info(
        "Retrieved %d chunks in %dms (mentioned=%s, threshold=%.2f)",
        len(chunks),
        elapsed_ms,
        mentioned or "—",
        settings.rag_similarity_threshold,
    )
    return chunks, elapsed_ms
