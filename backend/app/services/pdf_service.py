"""PDF validation and page-level text extraction via PyMuPDF."""

from __future__ import annotations

import hashlib
import logging
from pathlib import PurePath

import pymupdf as fitz

from app.config import get_settings
from app.models.domain import PageText

logger = logging.getLogger(__name__)


class PdfValidationError(ValueError):
    """Raised when an uploaded file fails PDF validation."""


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_pdf(filename: str, data: bytes) -> None:
    settings = get_settings()

    if not filename or PurePath(filename).suffix.lower() != ".pdf":
        raise PdfValidationError("Only PDF files are accepted.")

    if len(data) == 0:
        raise PdfValidationError("Uploaded file is empty.")

    if len(data) > settings.max_upload_bytes:
        limit_mb = settings.max_upload_bytes // (1024 * 1024)
        raise PdfValidationError(f"PDF exceeds the {limit_mb} MB size limit.")

    if not data.startswith(b"%PDF"):
        raise PdfValidationError("File does not look like a valid PDF (missing %PDF header).")


def display_name_from_filename(filename: str) -> str:
    """'Alpha Growth Fund.pdf' -> 'Alpha Growth Fund'."""
    return PurePath(filename).stem.strip()


def extract_pages(data: bytes) -> list[PageText]:
    """
    Open the PDF and extract text from each page separately.
    Page numbers are 1-based so citations match what humans see in a PDF viewer.
    """
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:  # noqa: BLE001 — surface as validation error
        raise PdfValidationError(f"Unable to open PDF: {exc}") from exc

    pages: list[PageText] = []
    try:
        for i in range(len(doc)):
            page = doc.load_page(i)
            text = page.get_text("text").strip()
            pages.append(PageText(page_number=i + 1, text=text))
    finally:
        doc.close()

    if not pages:
        raise PdfValidationError("PDF contains no pages.")

    non_empty = sum(1 for p in pages if p.text)
    logger.info("Extracted %d pages (%d with text)", len(pages), non_empty)
    return pages
