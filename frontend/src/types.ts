export interface DocumentItem {
  id: string
  filename: string
  display_name: string
  sha256: string
  page_count: number
  created_at: string
}

export interface Citation {
  document: string
  page: number
  quote: string
  similarity: number
}

export interface RetrievedChunk {
  document: string
  page: number
  content: string
  similarity: number
}

export interface Metrics {
  retrieval_ms: number
  generation_ms: number
  total_ms: number
}

export interface ChatResponse {
  answer: string
  citations: Citation[]
  retrieved_chunks: RetrievedChunk[]
  metrics: Metrics
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  response?: ChatResponse
}

export interface EvalCaseResult {
  id: string
  question: string
  answer: string
  expected_keywords: string[]
  keyword_hits: string[]
  keyword_pass: boolean
  document_hit: boolean
  page_hit: boolean
  expected_documents: string[]
  expected_pages: number[]
  retrieved_documents: string[]
  retrieved_pages: number[]
  top_similarity: number | null
  retrieval_ms: number
  generation_ms: number
  total_ms: number
  is_hallucination_test: boolean
  hallucination_pass: boolean | null
}

export interface EvaluationSummary {
  total_cases: number
  retrieval_source_accuracy: string
  retrieval_source_hits: number
  retrieval_source_total: number
  hallucination_test: string
  keyword_accuracy: string
  average_latency_s: number
  results: EvalCaseResult[]
}

export interface UploadResponse {
  document_id: string
  filename: string
  pages: number
  chunks_created: number
  already_ingested: boolean
}
