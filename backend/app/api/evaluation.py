"""Evaluation endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.evaluation import EvaluationSummary
from app.services.evaluation_service import run_evaluation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


@router.post("/run", response_model=EvaluationSummary)
def run_evals() -> EvaluationSummary:
    try:
        result = run_evaluation()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Evaluation failed")
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {exc}") from exc

    return EvaluationSummary.model_validate(result)
