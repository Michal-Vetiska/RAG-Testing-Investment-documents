"""Token-aware chunking that never crosses page boundaries."""

from __future__ import annotations

import logging

import tiktoken

from app.config import get_settings
from app.models.domain import PageText, TextChunk

logger = logging.getLogger(__name__)

# cl100k_base is the tokenizer used by OpenAI embedding / chat models we target.
_ENCODING_NAME = "cl100k_base"


def _encoding() -> tiktoken.Encoding:
    return tiktoken.get_encoding(_ENCODING_NAME)


def chunk_pages(pages: list[PageText]) -> list[TextChunk]:
    """
    Split each page independently into overlapping token windows.
    Staying inside a page keeps page_number accurate for citations.
    """
    settings = get_settings()
    chunk_size = settings.rag_chunk_size
    overlap = settings.rag_chunk_overlap

    if overlap >= chunk_size:
        raise ValueError("RAG_CHUNK_OVERLAP must be smaller than RAG_CHUNK_SIZE")

    enc = _encoding()
    chunks: list[TextChunk] = []
    global_index = 0

    for page in pages:
        text = page.text.strip()
        if not text:
            continue

        tokens = enc.encode(text)
        start = 0
        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            window = tokens[start:end]
            content = enc.decode(window).strip()
            if content:
                chunks.append(
                    TextChunk(
                        page_number=page.page_number,
                        chunk_index=global_index,
                        content=content,
                    )
                )
                global_index += 1

            if end >= len(tokens):
                break
            start = end - overlap

    logger.info(
        "Created %d chunks (size=%d, overlap=%d)",
        len(chunks),
        chunk_size,
        overlap,
    )
    return chunks
