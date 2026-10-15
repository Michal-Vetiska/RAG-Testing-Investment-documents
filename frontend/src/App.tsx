import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { askQuestion, fetchDocuments, runEvaluation, uploadDocument } from './api'
import type {
  ChatMessage,
  DocumentItem,
  EvaluationSummary,
} from './types'
import './App.css'

type Tab = 'chat' | 'evaluation'

function newId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

export default function App() {
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [question, setQuestion] = useState('')
  const [tab, setTab] = useState<Tab>('chat')
  const [debug, setDebug] = useState(false)
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({})
  const [loadingDocs, setLoadingDocs] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [asking, setAsking] = useState(false)
  const [evaluating, setEvaluating] = useState(false)
  const [evalResult, setEvalResult] = useState<EvaluationSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)

  const loadDocuments = useCallback(async () => {
    try {
      setLoadingDocs(true)
      const docs = await fetchDocuments()
      setDocuments(docs)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents')
    } finally {
      setLoadingDocs(false)
    }
  }, [])

  useEffect(() => {
    void loadDocuments()
  }, [loadDocuments])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, asking])

  async function handleUpload(file: File | undefined) {
    if (!file) return
    setUploading(true)
    setError(null)
    try {
      const result = await uploadDocument(file)
      await loadDocuments()
      if (result.already_ingested) {
        setError(`Already ingested: ${result.filename}`)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  async function handleSend(e?: FormEvent) {
    e?.preventDefault()
    const q = question.trim()
    if (!q || asking) return

    const userMsg: ChatMessage = { id: newId(), role: 'user', content: q }
    setMessages((prev) => [...prev, userMsg])
    setQuestion('')
    setAsking(true)
    setError(null)

    try {
      const response = await askQuestion(q)
      const assistantMsg: ChatMessage = {
        id: newId(),
        role: 'assistant',
        content: response.answer,
        response,
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chat failed')
    } finally {
      setAsking(false)
    }
  }

  async function handleEval() {
    setEvaluating(true)
    setError(null)
    try {
      const result = await runEvaluation()
      setEvalResult(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Evaluation failed')
    } finally {
      setEvaluating(false)
    }
  }

  function toggleSource(key: string) {
    setExpandedSources((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">IKC</div>
          <div>
            <h1>Investment Knowledge Copilot</h1>
            <p className="brand-sub">RAG over fund documentation</p>
          </div>
        </div>

        <section className="sidebar-section">
          <h2>Documents</h2>
          {loadingDocs && <p className="muted">Loading…</p>}
          {!loadingDocs && documents.length === 0 && (
            <p className="muted">No documents ingested yet.</p>
          )}
          <ul className="doc-list">
            {documents.map((doc) => (
              <li key={doc.id}>
                <span className="doc-name">{doc.display_name}</span>
                <span className="doc-meta">{doc.page_count} pages</span>
              </li>
            ))}
          </ul>
        </section>

        <div className="sidebar-footer">
          <input
            ref={fileRef}
            type="file"
            accept="application/pdf,.pdf"
            hidden
            onChange={(e) => void handleUpload(e.target.files?.[0])}
          />
          <button
            type="button"
            className="btn btn-primary"
            disabled={uploading}
            onClick={() => fileRef.current?.click()}
          >
            {uploading ? 'Uploading…' : 'Upload PDF'}
          </button>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <nav className="tabs">
            <button
              type="button"
              className={tab === 'chat' ? 'tab active' : 'tab'}
              onClick={() => setTab('chat')}
            >
              Chat
            </button>
            <button
              type="button"
              className={tab === 'evaluation' ? 'tab active' : 'tab'}
              onClick={() => setTab('evaluation')}
            >
              Evaluation
            </button>
          </nav>

          {tab === 'chat' && (
            <label className="debug-toggle">
              <input
                type="checkbox"
                checked={debug}
                onChange={(e) => setDebug(e.target.checked)}
              />
              RAG Debug
            </label>
          )}
        </header>

        {error && (
          <div className="banner error" role="alert">
            {error}
            <button type="button" className="banner-close" onClick={() => setError(null)}>
              ×
            </button>
          </div>
        )}

        {tab === 'chat' ? (
          <div className="chat-panel">
            <div className="chat-history">
              {messages.length === 0 && (
                <div className="empty-state">
                  <h2>Ask about ingested fund documents</h2>
                  <p>
                    Upload Alpha Growth Fund and Beta Income Fund PDFs, then ask grounded
                    questions. Answers include page-level citations.
                  </p>
                </div>
              )}

              {messages.map((msg) => (
                <article
                  key={msg.id}
                  className={msg.role === 'user' ? 'bubble user' : 'bubble assistant'}
                >
                  <div className="bubble-label">
                    {msg.role === 'user' ? 'Question' : 'Answer'}
                  </div>
                  <div className="bubble-body">{msg.content}</div>

                  {msg.role === 'assistant' && msg.response && (
                    <>
                      {msg.response.citations.length > 0 && (
                        <section className="sources">
                          <h3>Sources</h3>
                          <ul>
                            {msg.response.citations.map((c, i) => {
                              const key = `${msg.id}-c-${i}`
                              return (
                                <li key={key}>
                                  <button
                                    type="button"
                                    className="source-btn"
                                    onClick={() => toggleSource(key)}
                                  >
                                    {c.document} — Page {c.page}
                                    <span className="sim">
                                      {(c.similarity * 100).toFixed(1)}%
                                    </span>
                                  </button>
                                  {expandedSources[key] && (
                                    <blockquote className="quote">{c.quote}</blockquote>
                                  )}
                                </li>
                              )
                            })}
                          </ul>
                        </section>
                      )}

                      {debug && (
                        <section className="debug-panel">
                          <h3>Retrieval Debug</h3>
                          <p className="debug-meta">
                            Retrieved chunks: {msg.response.retrieved_chunks.length}
                          </p>
                          <div className="latency-row">
                            <span>Retrieval latency: {msg.response.metrics.retrieval_ms} ms</span>
                            <span>
                              Generation latency: {msg.response.metrics.generation_ms} ms
                            </span>
                            <span>Total latency: {msg.response.metrics.total_ms} ms</span>
                          </div>
                          {msg.response.retrieved_chunks.map((chunk, i) => (
                            <div key={`${msg.id}-chunk-${i}`} className="debug-chunk">
                              <div className="debug-chunk-head">
                                Chunk {i + 1} · {chunk.document} · Page {chunk.page} ·
                                Similarity: {chunk.similarity.toFixed(3)}
                              </div>
                              <pre>{chunk.content}</pre>
                            </div>
                          ))}
                        </section>
                      )}
                    </>
                  )}
                </article>
              ))}

              {asking && (
                <div className="bubble assistant pending">
                  <div className="bubble-label">Answer</div>
                  <div className="bubble-body">Retrieving and generating…</div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            <form className="composer" onSubmit={(e) => void handleSend(e)}>
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask a question about the funds…"
                disabled={asking}
                aria-label="Question"
              />
              <button type="submit" className="btn btn-primary" disabled={asking || !question.trim()}>
                Send
              </button>
            </form>
          </div>
        ) : (
          <div className="eval-panel">
            <div className="eval-header">
              <div>
                <h2>Evaluation</h2>
                <p className="muted">
                  Runs the fixed dataset in <code>evals/dataset.json</code> through retrieval +
                  generation. Checks document/page hits and expected keywords — no LLM-as-a-judge.
                </p>
              </div>
              <button
                type="button"
                className="btn btn-primary"
                disabled={evaluating}
                onClick={() => void handleEval()}
              >
                {evaluating ? 'Running…' : 'Run evaluation'}
              </button>
            </div>

            {evaluating && <p className="muted">Running evaluation cases — this may take a minute.</p>}

            {evalResult && (
              <>
                <div className="eval-summary">
                  <div className="metric-card">
                    <span className="metric-label">Retrieval source accuracy</span>
                    <span className="metric-value">{evalResult.retrieval_source_accuracy}</span>
                  </div>
                  <div className="metric-card">
                    <span className="metric-label">Hallucination test</span>
                    <span
                      className={
                        evalResult.hallucination_test === 'PASS'
                          ? 'metric-value pass'
                          : evalResult.hallucination_test === 'FAIL'
                            ? 'metric-value fail'
                            : 'metric-value'
                      }
                    >
                      {evalResult.hallucination_test}
                    </span>
                  </div>
                  <div className="metric-card">
                    <span className="metric-label">Keyword accuracy</span>
                    <span className="metric-value">{evalResult.keyword_accuracy}</span>
                  </div>
                  <div className="metric-card">
                    <span className="metric-label">Average latency</span>
                    <span className="metric-value">{evalResult.average_latency_s.toFixed(2)} s</span>
                  </div>
                </div>

                <table className="eval-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Doc hit</th>
                      <th>Page hit</th>
                      <th>Keywords</th>
                      <th>Top sim</th>
                      <th>Latency</th>
                      <th>Answer</th>
                    </tr>
                  </thead>
                  <tbody>
                    {evalResult.results.map((r) => (
                      <tr key={r.id}>
                        <td>
                          {r.id}
                          {r.is_hallucination_test && (
                            <span className="tag">hallucination</span>
                          )}
                        </td>
                        <td>{r.document_hit ? '✓' : '✗'}</td>
                        <td>{r.page_hit ? '✓' : '✗'}</td>
                        <td>
                          {r.is_hallucination_test
                            ? r.hallucination_pass
                              ? 'PASS'
                              : 'FAIL'
                            : r.keyword_pass
                              ? '✓'
                              : '✗'}
                        </td>
                        <td>
                          {r.top_similarity != null ? r.top_similarity.toFixed(3) : '—'}
                        </td>
                        <td>{(r.total_ms / 1000).toFixed(2)} s</td>
                        <td className="answer-cell">{r.answer}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
