"""
Simple keyword / source-hit evaluation — no LLM-as-a-judge.

Loads evals/dataset.json and runs each case through the RAG pipeline.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.config import ROOT_DIR
from app.services.rag_service import NOT_FOUND_ANSWER, answer_question

logger = logging.getLogger(__name__)

DATASET_PATH = ROOT_DIR / "evals" / "dataset.json"


def _load_dataset() -> list[dict[str, Any]]:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Evaluation dataset not found: {DATASET_PATH}")
    with DATASET_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    cases = data.get("cases") if isinstance(data, dict) else data
    if not isinstance(cases, list) or not cases:
        raise ValueError("Evaluation dataset is empty or invalid")
    return cases


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _keyword_hits(answer: str, keywords: list[str]) -> list[str]:
    norm_answer = _normalize(answer)
    hits: list[str] = []
    for kw in keywords:
        if _normalize(kw) in norm_answer:
            hits.append(kw)
    return hits


def _document_hit(
    retrieved_docs: list[str],
    expected_docs: list[str],
) -> bool:
    if not expected_docs:
        return True
    retrieved_lower = {d.lower() for d in retrieved_docs}
    return all(doc.lower() in retrieved_lower for doc in expected_docs)


def _page_hit(
    retrieved: list[dict[str, Any]],
    expected_docs: list[str],
    expected_pages: list[int],
    require_all_docs: bool,
) -> bool:
    """
    Check that expected pages appear among retrieved chunks.
    When require_all_docs is True (comparison questions), each expected
    document must contribute at least one of its expected pages.
    """
    if not expected_pages:
        return True

    if require_all_docs and expected_docs:
        for doc in expected_docs:
            pages_for_doc = {
                c["page"]
                for c in retrieved
                if c["document"].lower() == doc.lower()
            }
            if not pages_for_doc.intersection(expected_pages):
                return False
        return True

    retrieved_pages = {c["page"] for c in retrieved}
    # At least one expected page must appear (OR semantics for Alpha risk 1|3).
    return bool(retrieved_pages.intersection(expected_pages))


def run_evaluation() -> dict[str, Any]:
    cases = _load_dataset()
    results: list[dict[str, Any]] = []

    source_hits = 0
    source_total = 0
    keyword_hits_count = 0
    keyword_total = 0
    hallucination_status = "N/A"
    latencies: list[int] = []

    for case in cases:
        case_id = str(case.get("id", ""))
        question = case["question"]
        expected_keywords: list[str] = list(case.get("expected_keywords") or [])
        expected_docs: list[str] = list(case.get("expected_documents") or [])
        expected_pages: list[int] = [int(p) for p in (case.get("expected_pages") or [])]
        is_hallucination = bool(case.get("is_hallucination_test", False))
        require_all_docs = bool(case.get("require_all_documents", False))

        logger.info("Running eval case %s", case_id)
        response = answer_question(question)

        answer = response["answer"]
        retrieved = response["retrieved_chunks"]
        metrics = response["metrics"]
        latencies.append(int(metrics["total_ms"]))

        retrieved_docs = list({c["document"] for c in retrieved})
        retrieved_pages = [c["page"] for c in retrieved]
        top_sim = max((c["similarity"] for c in retrieved), default=None)

        doc_hit = _document_hit(retrieved_docs, expected_docs)
        page_ok = _page_hit(
            retrieved, expected_docs, expected_pages, require_all_docs
        )

        # Source accuracy: document hit AND page hit (when pages are specified).
        if expected_docs or expected_pages:
            source_total += 1
            if doc_hit and page_ok:
                source_hits += 1

        kw_hits = _keyword_hits(answer, expected_keywords)
        if expected_keywords:
            keyword_total += 1
            kw_pass = len(kw_hits) == len(expected_keywords)
            if kw_pass:
                keyword_hits_count += 1
        else:
            kw_pass = True

        hallucination_pass: bool | None = None
        if is_hallucination:
            hallucination_pass = NOT_FOUND_ANSWER.lower() in answer.lower()
            hallucination_status = "PASS" if hallucination_pass else "FAIL"

        results.append(
            {
                "id": case_id,
                "question": question,
                "answer": answer,
                "expected_keywords": expected_keywords,
                "keyword_hits": kw_hits,
                "keyword_pass": kw_pass,
                "document_hit": doc_hit,
                "page_hit": page_ok,
                "expected_documents": expected_docs,
                "expected_pages": expected_pages,
                "retrieved_documents": retrieved_docs,
                "retrieved_pages": retrieved_pages,
                "top_similarity": top_sim,
                "retrieval_ms": metrics["retrieval_ms"],
                "generation_ms": metrics["generation_ms"],
                "total_ms": metrics["total_ms"],
                "is_hallucination_test": is_hallucination,
                "hallucination_pass": hallucination_pass,
            }
        )

    avg_latency_s = (sum(latencies) / len(latencies) / 1000.0) if latencies else 0.0

    return {
        "total_cases": len(results),
        "retrieval_source_accuracy": f"{source_hits} / {source_total}",
        "retrieval_source_hits": source_hits,
        "retrieval_source_total": source_total,
        "hallucination_test": hallucination_status,
        "keyword_accuracy": f"{keyword_hits_count} / {keyword_total}",
        "average_latency_s": round(avg_latency_s, 3),
        "results": results,
    }
