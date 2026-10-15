"""Pydantic schemas for document endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentOut(BaseModel):
    id: UUID
    filename: str
    display_name: str
    sha256: str
    page_count: int
    created_at: datetime


class UploadResponse(BaseModel):
    document_id: UUID
    filename: str
    pages: int
    chunks_created: int
    already_ingested: bool = False
