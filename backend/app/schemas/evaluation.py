"""Pydantic schemas for evaluation endpoints."""

from pydantic import BaseModel


class EvalCaseResult(BaseModel):
    id: str
    question: str
    answer: str
    expected_keywords: list[str]
    keyword_hits: list[str]
    keyword_pass: bool
    document_hit: bool
    page_hit: bool
    expected_documents: list[str]
    expected_pages: list[int]
    retrieved_documents: list[str]
    retrieved_pages: list[int]
    top_similarity: float | None
    retrieval_ms: int
    generation_ms: int
    total_ms: int
    is_hallucination_test: bool
    hallucination_pass: bool | None


class EvaluationSummary(BaseModel):
    total_cases: int
    retrieval_source_accuracy: str
    retrieval_source_hits: int
    retrieval_source_total: int
    hallucination_test: str
    keyword_accuracy: str
    average_latency_s: float
    results: list[EvalCaseResult]
