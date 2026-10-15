"""Internal domain dataclasses used across services."""

from dataclasses import dataclass
from typing import Any


@dataclass
class PageText:
    page_number: int
    text: str


@dataclass
class TextChunk:
    page_number: int
    chunk_index: int
    content: str


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    document: str
    filename: str
    page: int
    content: str
    similarity: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "document": self.document,
            "filename": self.filename,
            "page": self.page,
            "content": self.content,
            "similarity": self.similarity,
        }


@dataclass
class Citation:
    document: str
    page: int
    quote: str
    similarity: float
