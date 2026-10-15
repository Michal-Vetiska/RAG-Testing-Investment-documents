"""Pydantic schemas for chat / RAG endpoints."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)


class CitationOut(BaseModel):
    document: str
    page: int
    quote: str
    similarity: float


class RetrievedChunkOut(BaseModel):
    document: str
    page: int
    content: str
    similarity: float


class MetricsOut(BaseModel):
    retrieval_ms: int
    generation_ms: int
    total_ms: int


class ChatResponse(BaseModel):
    answer: str
    citations: list[CitationOut]
    retrieved_chunks: list[RetrievedChunkOut]
    metrics: MetricsOut
