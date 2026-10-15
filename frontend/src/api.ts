import type {
  ChatResponse,
  DocumentItem,
  EvaluationSummary,
  UploadResponse,
} from './types'

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json()
    if (typeof data?.detail === 'string') return data.detail
    return JSON.stringify(data)
  } catch {
    return res.statusText || 'Request failed'
  }
}

export async function fetchDocuments(): Promise<DocumentItem[]> {
  const res = await fetch('/api/documents')
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch('/api/documents/upload', {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function askQuestion(question: string): Promise<ChatResponse> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function runEvaluation(): Promise<EvaluationSummary> {
  const res = await fetch('/api/evaluation/run', { method: 'POST' })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}
