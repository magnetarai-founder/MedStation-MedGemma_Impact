import { useState, useEffect, useRef } from 'react'
import { askNLQ, NLQResponse } from '@/lib/nlqApi'
import { Loader2, X, Copy, Check, HelpCircle, Play, History, StopCircle } from 'lucide-react'
import api from '@/lib/api'

interface NLQueryPanelProps {
  onClose: () => void
}

interface HistoryItem {
  id: string
  question: string
  sql: string
  summary: string | null
  created_at: string
}

export function NLQueryPanel({ onClose }: NLQueryPanelProps) {
  const [question, setQuestion] = useState('')
  const [sessionId, setSessionId] = useState('')
  const [datasetId, setDatasetId] = useState('')
  const [model, setModel] = useState('qwen2.5:7b-instruct')
  const [loading, setLoading] = useState(false)
  const [runningSQL, setRunningSQL] = useState(false)
  const [resp, setResp] = useState<NLQResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showSql, setShowSql] = useState(true)
  const [copied, setCopied] = useState(false)
  const [showHelp, setShowHelp] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [loadingHistory, setLoadingHistory] = useState(false)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Fetch recent history
  const fetchHistory = async () => {
    setLoadingHistory(true)
    try {
      const response = await api.get('/api/v1/data/nlq/recent?limit=20')
      setHistory(response.data || [])
    } catch (e) {
      console.error('Failed to fetch NLQ history:', e)
      setHistory([])
    } finally {
      setLoadingHistory(false)
    }
  }

  // Load history on mount
  useEffect(() => {
    fetchHistory()
  }, [])

  const onCancelAsk = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setLoading(false)
    setError('Request cancelled')
  }

  const onAsk = async () => {
    if (!question.trim() || question.trim().length < 3) {
      setError('Please enter a question (at least 3 characters)')
      return
    }

    if (!sessionId && !datasetId) {
      setError('Please provide either a Session ID or Dataset ID')
      return
    }

    setLoading(true)
    setError(null)
    setResp(null)

    // Create new AbortController for this request
    abortControllerRef.current = new AbortController()

    try {
      const res = await askNLQ({
        question: question.trim(),
        session_id: sessionId || undefined,
        dataset_id: datasetId || undefined,
        model: model || undefined,
      }, abortControllerRef.current.signal)

      // Check for backend error response
      if (res.error) {
        setError(res.error + (res.suggestion ? ` (${res.suggestion})` : ''))
        return
      }

      setResp(res)
      // Refresh history after successful query
      fetchHistory()
    } catch (e: any) {
      if (e.name === 'AbortError') {
        // Request was cancelled, error already set by onCancelAsk
        return
      }
      setError(e?.message || 'Failed to process question. Please try again.')
    } finally {
      setLoading(false)
      abortControllerRef.current = null
    }
  }

  const onRunSQL = async () => {
    if (!resp?.sql) return

    setRunningSQL(true)
    setError(null)
    try {
      // Re-execute the current SQL using the data engine
      const tableName = resp.metadata?.table_name || 'unknown'
      const payload = {
        sql: resp.sql,
        table_name: tableName
      }

      // Use existing session query endpoint if session_id exists
      if (sessionId) {
        const result = await api.post(`/api/sessions/${sessionId}/query`, payload)

        // Transform to NLQResponse format
        const refreshedResp: NLQResponse = {
          ...resp,
          results: result.data.rows || [],
          row_count: result.data.row_count || 0,
          columns: result.data.columns || [],
          metadata: {
            ...resp.metadata,
            execution_time_ms: result.data.execution_time || 0,
            total_time_ms: result.data.execution_time || 0
          }
        }
        setResp(refreshedResp)
      } else {
        // For dataset-only queries, just show the existing results
        setError('Re-run SQL requires a Session ID. Results below are from the original query.')
      }
    } catch (e: any) {
      setError(e?.message || 'Failed to re-run SQL')
    } finally {
      setRunningSQL(false)
    }
  }

  const copySql = async () => {
    if (!resp?.sql) return
    await navigator.clipboard.writeText(resp.sql)
    setCopied(true)
    setTimeout(() => setCopied(false), 1200)
  }

  // Simple table renderer for NLQ results (avoid coupling to session stores)
  const renderTable = () => {
    if (!resp?.results || !resp?.columns) return null
    const rows = Array.isArray(resp.results) ? resp.results : []
    const cols = Array.isArray(resp.columns) ? resp.columns : []
    const MAX_ROWS = 200
    const viewRows = rows.slice(0, MAX_ROWS)
    const truncated = rows.length > MAX_ROWS

    return (
      <div className="mt-3 border rounded bg-white/60 dark:bg-gray-800/40 overflow-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="bg-gray-100/60 dark:bg-gray-900/40">
              {cols.map((c) => (
                <th key={c} className="text-left px-2 py-1.5 font-medium text-gray-700 dark:text-gray-300 border-b">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {viewRows.map((r: any, i: number) => (
              <tr key={i} className={i % 2 ? 'bg-gray-50/40 dark:bg-gray-900/20' : ''}>
                {cols.map((c) => (
                  <td key={c} className="px-2 py-1 border-b text-gray-800 dark:text-gray-200">
                    {String(r?.[c] ?? '')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {truncated && (
          <div className="px-2 py-1 text-xs text-gray-500">Showing first {MAX_ROWS} rows</div>
        )}
      </div>
    )}

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-[900px] max-w-[95vw] max-h-[90vh] overflow-auto rounded-xl shadow-xl border bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <h3 className="text-base font-semibold">Ask AI About Your Data</h3>
            <span className="text-xs text-gray-500">⌘K D</span>
            {/* History Button */}
            <button
              onClick={() => setShowHistory(!showHistory)}
              className="flex items-center gap-1.5 px-2 py-1 text-xs rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400"
            >
              <History className="w-3.5 h-3.5" />
              Recent
            </button>
          </div>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-4">
          <div className="grid grid-cols-1 gap-3">
            {/* Recent Analyses Dropdown */}
            {showHistory && (
              <div className="bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-lg p-3 max-h-60 overflow-auto">
                <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Recent Analyses</div>
                {loadingHistory ? (
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Loading...
                  </div>
                ) : history.length === 0 ? (
                  <div className="text-sm text-gray-500">No recent analyses found</div>
                ) : (
                  <div className="space-y-2">
                    {history.map((item) => (
                      <button
                        key={item.id}
                        onClick={() => {
                          setQuestion(item.question)
                          setShowSql(true)
                          setShowHistory(false)
                        }}
                        className="w-full text-left p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-600"
                      >
                        <div className="text-sm text-gray-800 dark:text-gray-200 mb-1">
                          {item.question}
                        </div>
                        <div className="text-xs font-mono text-gray-500 dark:text-gray-400 truncate">
                          {item.sql}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Dataset/Session Picker */}
            <div className="bg-blue-50/50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Data Source
                </label>
                <button
                  onClick={() => setShowHelp(!showHelp)}
                  className="text-xs text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
                >
                  <HelpCircle className="w-3.5 h-3.5" />
                  How to find IDs
                </button>
              </div>

              {showHelp && (
                <div className="mb-3 text-xs text-gray-600 dark:text-gray-400 bg-white/50 dark:bg-gray-800/50 p-2 rounded border">
                  <p className="mb-1"><strong>Session ID:</strong> Upload a CSV/Excel in Data Workspace, then check the browser DevTools (Network tab) or API response for the session UUID.</p>
                  <p><strong>Dataset ID:</strong> Use the dataset UUID from your uploaded files (found in API responses or database).</p>
                  <p className="mt-1 text-blue-600 dark:text-blue-400">
                    <a href="http://localhost:8000/api/docs" target="_blank" rel="noopener noreferrer" className="underline">
                      → Open API Docs (Swagger)
                    </a>
                  </p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-2">
                <input
                  value={sessionId}
                  onChange={(e) => setSessionId(e.target.value)}
                  placeholder="Session ID (paste UUID)"
                  className="rounded border px-3 py-2 bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-700 text-sm"
                />
                <input
                  value={datasetId}
                  onChange={(e) => setDatasetId(e.target.value)}
                  placeholder="Dataset ID (paste UUID)"
                  className="rounded border px-3 py-2 bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-700 text-sm"
                />
              </div>
              <div className="mt-2">
                <input
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  placeholder="AI Model (default: qwen2.5:7b-instruct)"
                  className="w-full rounded border px-3 py-2 bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-700 text-sm"
                />
              </div>
            </div>

            {/* Question Input */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Your Question
              </label>
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="e.g., Show the top 10 customers by revenue&#10;e.g., What's the average order value by region?&#10;e.g., Find all transactions above $1000 last month"
                rows={3}
                className="w-full rounded border px-3 py-2 bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-700"
              />
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-2">
              {loading ? (
                <button
                  onClick={onCancelAsk}
                  className="px-4 py-2 rounded-md text-white bg-red-600 hover:bg-red-700 flex items-center gap-2"
                >
                  <StopCircle className="w-4 h-4" />
                  <span>Cancel</span>
                </button>
              ) : (
                <button
                  onClick={onAsk}
                  disabled={!question.trim() || (!sessionId && !datasetId)}
                  className={`px-4 py-2 rounded-md text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2`}
                >
                  <span>Ask AI</span>
                </button>
              )}

              {resp?.sql && !loading && (
                <button
                  onClick={onRunSQL}
                  disabled={runningSQL}
                  className="px-4 py-2 rounded-md text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-50 flex items-center gap-2"
                >
                  {runningSQL ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                  <span>{runningSQL ? 'Running…' : 'Run SQL'}</span>
                </button>
              )}
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
                <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
              </div>
            )}

            {/* Empty State */}
            {!resp && !loading && !error && (
              <div className="mt-4 text-center text-sm text-gray-500 dark:text-gray-400 py-8">
                <p>Enter a question about your data and click "Ask AI" to get started.</p>
                <p className="mt-1">Make sure to provide either a Session ID or Dataset ID above.</p>
              </div>
            )}

            {resp && (
              <div className="mt-3">
                {/* Summary */}
                {resp.summary && (
                  <div className="mb-2 text-sm text-gray-800 dark:text-gray-200">{resp.summary}</div>
                )}

                {/* SQL block */}
                {resp.sql && (
                  <div className="mb-2">
                    <div className="flex items-center justify-between">
                      <label className="flex items-center gap-2 text-sm">
                        <input type="checkbox" checked={showSql} onChange={() => setShowSql(!showSql)} />
                        Show generated SQL
                      </label>
                      <button onClick={copySql} className="text-xs flex items-center gap-1 px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
                        {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                        {copied ? 'Copied' : 'Copy'}
                      </button>
                    </div>
                    {showSql && (
                      <pre className="mt-1 p-2 rounded bg-gray-50 dark:bg-gray-900/50 overflow-auto text-xs border border-gray-200 dark:border-gray-700">
                        {resp.sql}
                      </pre>
                    )}
                  </div>
                )}

                {/* Warnings */}
                {resp.warnings && resp.warnings.length > 0 && (
                  <div className="text-xs text-amber-600 dark:text-amber-400 mb-2">
                    {resp.warnings.map((w, i) => (
                      <div key={i}>• {w}</div>
                    ))}
                  </div>
                )}

                {/* Results */}
                {renderTable()}

                {/* Metadata */}
                {resp.metadata && (
                  <div className="mt-2 text-xs text-gray-500">
                    Time: {resp.metadata.total_time_ms ?? resp.metadata.execution_time_ms} ms
                    {resp.metadata.truncated ? ' • Results truncated' : ''}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

