"""FastAPI entrypoint for Investment Knowledge Copilot."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, documents, evaluation
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info(
        "Investment Knowledge Copilot started (CORS origin=%s)",
        settings.cors_origin,
    )
    yield


app = FastAPI(
    title="Investment Knowledge Copilot",
    description="RAG PoC over investment fund PDF documentation",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(evaluation.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
