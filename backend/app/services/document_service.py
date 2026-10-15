"""Document persistence: list, dedupe by SHA-256, store chunks + embeddings."""

from __future__ import annotations

import logging
from typing import Any

from app.database import get_supabase
from app.services.chunking_service import chunk_pages
from app.services.embedding_service import embed_texts
from app.services.pdf_service import (
    PdfValidationError,
    compute_sha256,
    display_name_from_filename,
    extract_pages,
    validate_pdf,
)

logger = logging.getLogger(__name__)


def list_documents() -> list[dict[str, Any]]:
    client = get_supabase()
    result = (
        client.table("documents")
        .select("id, filename, display_name, sha256, page_count, created_at")
        .order("created_at", desc=False)
        .execute()
    )
    return result.data or []


def find_by_sha256(sha256: str) -> dict[str, Any] | None:
    client = get_supabase()
    result = (
        client.table("documents")
        .select("id, filename, display_name, sha256, page_count, created_at")
        .eq("sha256", sha256)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def ingest_pdf(filename: str, data: bytes) -> dict[str, Any]:
    """
    Full ingestion pipeline:
    validate -> hash -> dedupe -> extract pages -> chunk -> embed -> store
    """
    validate_pdf(filename, data)
    sha256 = compute_sha256(data)

    existing = find_by_sha256(sha256)
    if existing:
        logger.info("Document already ingested (sha256=%s)", sha256[:12])
        return {
            "document_id": existing["id"],
            "filename": existing["filename"],
            "pages": existing["page_count"],
            "chunks_created": 0,
            "already_ingested": True,
        }

    pages = extract_pages(data)
    chunks = chunk_pages(pages)
    if not chunks:
        raise PdfValidationError(
            "No extractable text found in the PDF. Scanned/image-only PDFs are not supported."
        )

    embeddings = embed_texts([c.content for c in chunks])
    display_name = display_name_from_filename(filename)
    client = get_supabase()

    doc_insert = (
        client.table("documents")
        .insert(
            {
                "filename": filename,
                "display_name": display_name,
                "sha256": sha256,
                "page_count": len(pages),
            }
        )
        .execute()
    )
    document = (doc_insert.data or [None])[0]
    if not document:
        raise RuntimeError("Failed to insert document row")

    document_id = document["id"]
    rows = [
        {
            "document_id": document_id,
            "page_number": chunk.page_number,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "embedding": embedding,
        }
        for chunk, embedding in zip(chunks, embeddings, strict=True)
    ]

    # Insert in batches to stay within PostgREST payload limits.
    batch_size = 50
    for i in range(0, len(rows), batch_size):
        client.table("document_chunks").insert(rows[i : i + batch_size]).execute()

    logger.info(
        "Ingested document %s (%s): %d pages, %d chunks",
        display_name,
        document_id,
        len(pages),
        len(chunks),
    )

    return {
        "document_id": document_id,
        "filename": filename,
        "pages": len(pages),
        "chunks_created": len(chunks),
        "already_ingested": False,
    }


def list_display_names() -> list[str]:
    docs = list_documents()
    return [d["display_name"] for d in docs]
