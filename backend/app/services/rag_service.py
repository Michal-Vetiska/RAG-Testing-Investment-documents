"""
RAG generation: grounded prompt + chat LLM + structured citations.

Retrieval stays in retrieval_service — this module only builds context and calls the LLM.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from app.config import get_settings
from app.models.domain import Citation, RetrievedChunk
from app.openai_client import chat_client
from app.services.retrieval_service import retrieve

logger = logging.getLogger(__name__)

NOT_FOUND_ANSWER = "Informace nebyla v poskytnutých dokumentech nalezena."

SYSTEM_PROMPT = """You are an assistant working with investment fund documentation.

Answer ONLY using information contained in PROVIDED CONTEXT.

Never invent missing facts.

If the context does not contain enough information to answer the question, explicitly say that the information was not found in the supplied documents.

Do not use your general knowledge to fill missing information.

Whenever you make a factual claim, ground it in the supplied sources.

Do not provide personalized investment advice.

You MUST respond with a single JSON object only (no markdown fences), with this shape:
{
  "information_found": true or false,
  "answer": "string — if information_found is false, use exactly: Informace nebyla v poskytnutých dokumentech nalezena.",
  "used_sources": [1, 2]
}

used_sources must be 1-based SOURCE indices from the provided context that support the answer.
If information_found is false, used_sources must be an empty array.
"""


def _short_quote(content: str, max_chars: int = 240) -> str:
    """Short citation quote from stored chunk text — never invented by the LLM."""
    text = " ".join(content.split())
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    # Prefer ending on a sentence boundary when possible.
    for sep in (". ", "; ", ", "):
        idx = cut.rfind(sep)
        if idx >= max_chars // 2:
            return cut[: idx + 1].strip() + "…"
    return cut.rsplit(" ", 1)[0].strip() + "…"


def _build_context(chunks: list[RetrievedChunk]) -> str:
    parts: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        parts.append(
            f"[SOURCE {i}]\n"
            f"Document: {chunk.document}\n"
            f"Page: {chunk.page}\n"
            f"Similarity: {chunk.similarity:.3f}\n"
            f"Content:\n{chunk.content}"
        )
    return "\n\n".join(parts)


def _parse_llm_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    # Tolerate accidental markdown fences.
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: treat whole string as answer if JSON parse fails.
        logger.warning("LLM returned non-JSON; using raw text as answer")
        found = NOT_FOUND_ANSWER.lower() not in text.lower()
        return {
            "information_found": found,
            "answer": text if found else NOT_FOUND_ANSWER,
            "used_sources": list(range(1, 7)) if found else [],
        }


def _build_citations(
    chunks: list[RetrievedChunk],
    used_sources: list[Any],
) -> list[Citation]:
    citations: list[Citation] = []
    seen: set[tuple[str, int]] = set()
    for raw_idx in used_sources:
        try:
            idx = int(raw_idx)
        except (TypeError, ValueError):
            continue
        if idx < 1 or idx > len(chunks):
            continue
        chunk = chunks[idx - 1]
        key = (chunk.document, chunk.page)
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            Citation(
                document=chunk.document,
                page=chunk.page,
                quote=_short_quote(chunk.content),
                similarity=chunk.similarity,
            )
        )
    return citations


def answer_question(question: str) -> dict[str, Any]:
    """
    Full RAG path:
    question -> retrieval -> (optional) grounded LLM -> answer + citations + metrics
    """
    total_started = time.perf_counter()
    chunks, retrieval_ms = retrieve(question)

    if not chunks:
        total_ms = int((time.perf_counter() - total_started) * 1000)
        logger.info("No chunks above threshold — skipping LLM")
        return {
            "answer": NOT_FOUND_ANSWER,
            "citations": [],
            "retrieved_chunks": [],
            "metrics": {
                "retrieval_ms": retrieval_ms,
                "generation_ms": 0,
                "total_ms": total_ms,
            },
        }

    settings = get_settings()
    context = _build_context(chunks)
    user_prompt = (
        f"PROVIDED CONTEXT:\n\n{context}\n\n"
        f"USER QUESTION:\n{question.strip()}"
    )

    gen_started = time.perf_counter()
    client = chat_client()
    # Official OpenAI accepts response_format=json_object.
    # LM Studio only allows json_schema | text — so skip it for local servers.
    create_kwargs: dict[str, Any] = {
        "model": settings.openai_chat_model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }
    if not settings.openai_base_url:
        create_kwargs["response_format"] = {"type": "json_object"}

    completion = client.chat.completions.create(**create_kwargs)
    generation_ms = int((time.perf_counter() - gen_started) * 1000)
    raw = completion.choices[0].message.content or "{}"
    parsed = _parse_llm_json(raw)

    information_found = bool(parsed.get("information_found", False))
    if not information_found:
        answer = NOT_FOUND_ANSWER
        citations: list[Citation] = []
    else:
        answer = str(parsed.get("answer") or "").strip() or NOT_FOUND_ANSWER
        if NOT_FOUND_ANSWER.lower() in answer.lower() and len(answer) < 120:
            answer = NOT_FOUND_ANSWER
            citations = []
        else:
            used = parsed.get("used_sources") or []
            if not isinstance(used, list):
                used = []
            citations = _build_citations(chunks, used)
            # If the model claimed a hit but cited nothing, attach top chunk as fallback.
            if not citations and chunks:
                citations = _build_citations(chunks, [1])

    total_ms = int((time.perf_counter() - total_started) * 1000)
    logger.info(
        "RAG done: retrieval=%dms generation=%dms total=%dms citations=%d",
        retrieval_ms,
        generation_ms,
        total_ms,
        len(citations),
    )

    return {
        "answer": answer,
        "citations": [
            {
                "document": c.document,
                "page": c.page,
                "quote": c.quote,
                "similarity": c.similarity,
            }
            for c in citations
        ],
        "retrieved_chunks": [
            {
                "document": c.document,
                "page": c.page,
                "content": c.content,
                "similarity": c.similarity,
            }
            for c in chunks
        ],
        "metrics": {
            "retrieval_ms": retrieval_ms,
            "generation_ms": generation_ms,
            "total_ms": total_ms,
        },
    }
