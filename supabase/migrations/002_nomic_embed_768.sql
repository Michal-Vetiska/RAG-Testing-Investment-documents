-- Switch embedding column from 1536 (OpenAI small) to 768 (nomic-embed-text-v1.5).
-- Safe when tables are empty / PoC re-ingest is expected.

DROP FUNCTION IF EXISTS match_document_chunks(vector(1536), float, int);
DROP FUNCTION IF EXISTS match_document_chunks(vector, float, int);

DROP TABLE IF EXISTS document_chunks CASCADE;

CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_document_chunks_document_id ON document_chunks(document_id);

CREATE INDEX idx_document_chunks_embedding_hnsw
    ON document_chunks
    USING hnsw (embedding vector_cosine_ops);

ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;

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
