-- Investment Knowledge Copilot — initial schema
-- Apply this in the Supabase SQL editor (or via supabase db push).

-- Enable pgvector for embedding storage and similarity search.
CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------------------
-- documents: one row per ingested PDF
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    display_name TEXT NOT NULL,
    sha256 TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    page_count INTEGER NOT NULL DEFAULT 0
);

-- ---------------------------------------------------------------------------
-- document_chunks: page-bounded text chunks with embeddings
-- Dimension 768 matches nomic-embed-text-v1.5 (LM Studio / local).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id
    ON document_chunks(document_id);

-- HNSW index for cosine distance (operator class vector_cosine_ops uses <=>).
-- Cosine distance != cosine similarity.
-- Cosine distance  = 1 - cosine similarity  (0 = identical direction).
-- Cosine similarity = 1 - cosine distance.
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw
    ON document_chunks
    USING hnsw (embedding vector_cosine_ops);

-- ---------------------------------------------------------------------------
-- RLS: enable, no anon policies — backend uses the service role key.
-- ---------------------------------------------------------------------------
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------------
-- RPC: vector similarity search over chunks
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION match_document_chunks(
    query_embedding vector(768),
    match_threshold float,
    match_count int
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    filename TEXT,
    display_name TEXT,
    page_number INTEGER,
    content TEXT,
    similarity FLOAT
)
LANGUAGE sql
STABLE
SET search_path = public
AS $$
    -- <=> returns cosine DISTANCE (lower is more similar).
    -- similarity = 1 - distance  so higher means more similar.
    SELECT
        c.id AS chunk_id,
        c.document_id,
        d.filename,
        d.display_name,
        c.page_number,
        c.content,
        (1 - (c.embedding <=> query_embedding))::float AS similarity
    FROM document_chunks c
    JOIN documents d ON d.id = c.document_id
    WHERE (1 - (c.embedding <=> query_embedding)) >= match_threshold
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
$$;

GRANT EXECUTE ON FUNCTION match_document_chunks(vector(768), float, int) TO service_role;
GRANT EXECUTE ON FUNCTION match_document_chunks(vector(768), float, int) TO anon;
GRANT EXECUTE ON FUNCTION match_document_chunks(vector(768), float, int) TO authenticated;
