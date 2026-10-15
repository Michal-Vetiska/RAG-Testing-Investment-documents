"""Document upload and listing endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.documents import DocumentOut, UploadResponse
from app.services.document_service import ingest_pdf, list_documents
from app.services.pdf_service import PdfValidationError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("", response_model=list[DocumentOut])
def get_documents() -> list[DocumentOut]:
    try:
        rows = list_documents()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to list documents")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return [DocumentOut.model_validate(row) for row in rows]


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    filename = file.filename or "upload.pdf"
    data = await file.read()

    try:
        result = ingest_pdf(filename, data)
    except PdfValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.exception("Ingestion configuration error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ingestion failed")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc

    return UploadResponse(
        document_id=result["document_id"],
        filename=result["filename"],
        pages=result["pages"],
        chunks_created=result["chunks_created"],
        already_ingested=result["already_ingested"],
    )
