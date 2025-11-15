export interface NLQRequest {
  question: string
  dataset_id?: string
  session_id?: string
  model?: string
}

export interface NLQResponse {
  sql?: string
  results?: any[]
  row_count?: number
  columns?: string[]
  summary?: string
  warnings?: string[]
  metadata?: Record<string, any>
  error?: string
  details?: string
  suggestion?: string
}

export async function askNLQ(body: NLQRequest, signal?: AbortSignal): Promise<NLQResponse> {
  const res = await fetch('/api/v1/data/nlq', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })

  // Backend returns 200 with error field for most validation issues
  if (!res.ok) {
    let detail: any = undefined
    try { detail = await res.json() } catch {}
    throw new Error(detail?.error || detail?.detail || res.statusText)
  }

  return res.json()
}

