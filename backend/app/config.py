"""Application settings loaded from environment / .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Monorepo root: backend/app/config.py -> ../../
ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    # Optional OpenAI-compatible base URL (e.g. LM Studio: http://127.0.0.1:1234/v1)
    openai_base_url: str = ""
    # Optional separate base URL for embeddings only
    openai_embedding_base_url: str = ""
    openai_chat_model: str = ""
    openai_embedding_model: str = ""

    supabase_url: str = ""
    supabase_service_role_key: str = ""

    rag_top_k: int = 6
    rag_similarity_threshold: float = 0.45
    rag_chunk_size: int = 700
    rag_chunk_overlap: int = 120

    cors_origin: str = "http://localhost:5173"

    # Must match document_chunks.embedding vector(N) in the DB migration.
    # nomic-embed-text-v1.5 = 768; text-embedding-3-small = 1536
    embedding_dimensions: int = 768
    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB
    openai_timeout_seconds: float = 60.0
    embedding_batch_size: int = 64

    def require_openai(self) -> None:
        missing = []
        if not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if not self.openai_chat_model:
            missing.append("OPENAI_CHAT_MODEL")
        if not self.openai_embedding_model:
            missing.append("OPENAI_EMBEDDING_MODEL")
        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

    def require_supabase(self) -> None:
        missing = []
        if not self.supabase_url:
            missing.append("SUPABASE_URL")
        if not self.supabase_service_role_key:
            missing.append("SUPABASE_SERVICE_ROLE_KEY")
        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}"
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
