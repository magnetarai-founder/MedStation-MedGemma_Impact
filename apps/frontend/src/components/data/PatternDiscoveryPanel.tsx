import { useState } from 'react'
import { Loader2, X, Download, HelpCircle, TrendingUp, BarChart3, AlertCircle } from 'lucide-react'
import api from '@/lib/api'

interface PatternDiscoveryPanelProps {
  onClose: () => void
}

interface ColumnStats {
  type: 'numeric' | 'categorical' | 'temporal' | 'text'
  [key: string]: any
}

interface Correlation {
  col1: string
  col2: string
  method: string
  r: number
}

interface PatternResponse {
  columns: Record<string, ColumnStats>
  correlations: Correlation[]
  insights: string[]
  metadata: {
    total_rows: number
    sampled: boolean
    total_time_ms: number
    warnings?: string[]
  }
}

export function PatternDiscoveryPanel({ onClose }: PatternDiscoveryPanelProps) {
  const [sessionId, setSessionId] = useState('')
  const [datasetId, setDatasetId] = useState('')
  const [tableName, setTableName] = useState('')
  const [sampleRows, setSampleRows] = useState('50000')
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<PatternResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showHelp, setShowHelp] = useState(false)

  const onDiscover = async () => {
    if (!sessionId && !datasetId) {
      setError('Please provide either a Session ID or Dataset ID')
      return
    }

    if (sessionId && !tableName) {
      setError('Table name is required when using Session ID')
      return
    }

    setLoading(true)
    setError(null)
    setResponse(null)

    try {
      const payload: any = {}
      if (sessionId) payload.session_id = sessionId
      if (datasetId) payload.dataset_id = datasetId
      if (tableName) payload.table_name = tableName
      if (sampleRows) payload.sample_rows = parseInt(sampleRows, 10)

      const res = await api.post('/api/v1/data/discover-patterns', payload)
      setResponse(res.data)
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      if (typeof detail === 'string') {
        setError(detail)
      } else if (detail?.error) {
        setError(detail.error + (detail.suggestion ? ` (${detail.suggestion})` : ''))
      } else {
        setError(e?.message || 'Failed to discover patterns')
      }
    } finally {
      setLoading(false)
    }
  }

  const downloadJSON = () => {
    if (!response) return
    const blob = new Blob([JSON.stringify(response, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `pattern-discovery-${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const downloadPDF = async () => {
    if (!response) return

    // Simple PDF export using browser print (jspdf can be added later if needed)
    const printWindow = window.open('', '_blank')
    if (!printWindow) return

    const html = `
      <html>
        <head>
          <title>Pattern Discovery Report</title>
          <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1 { color: #333; }
            h2 { color: #555; margin-top: 20px; }
            .stat-card { border: 1px solid #ddd; padding: 10px; margin: 10px 0; border-radius: 4px; }
            .insight { margin: 5px 0; }
            table { border-collapse: collapse; width: 100%; margin: 10px 0; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f4f4f4; }
          </style>
        </head>
        <body>
          <h1>Pattern Discovery Report</h1>
          <p><strong>Generated:</strong> ${new Date().toLocaleString()}</p>
          <p><strong>Total Rows:</strong> ${response.metadata.total_rows.toLocaleString()}</p>
          ${response.metadata.sampled ? '<p><em>Note: Results based on sample data</em></p>' : ''}

          <h2>Insights</h2>
          ${response.insights.map(i => `<div class="insight">• ${i}</div>`).join('')}

          <h2>Columns (${Object.keys(response.columns).length})</h2>
          ${Object.entries(response.columns).map(([name, stats]) => `
            <div class="stat-card">
              <strong>${name}</strong> <em>(${stats.type})</em>
              <pre>${JSON.stringify(stats, null, 2)}</pre>
            </div>
          `).join('')}

          <h2>Correlations</h2>
          <table>
            <tr><th>Column 1</th><th>Column 2</th><th>Correlation (r)</th></tr>
            ${response.correlations.map(c => `
              <tr><td>${c.col1}</td><td>${c.col2}</td><td>${c.r.toFixed(3)}</td></tr>
            `).join('')}
          </table>
        </body>
      </html>
    `

    printWindow.document.write(html)
    printWindow.document.close()
    printWindow.print()
  }

  const renderColumnCard = (colName: string, stats: ColumnStats) => {
    return (
      <div key={colName} className="border rounded-lg p-3 bg-white/60 dark:bg-gray-800/40">
        <div className="flex items-center justify-between mb-2">
          <h4 className="font-medium text-gray-900 dark:text-gray-100">{colName}</h4>
          <span className="text-xs px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200">
            {stats.type}
          </span>
        </div>

        {stats.type === 'numeric' && (
          <div className="text-sm space-y-1">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Range:</span>
              <span className="font-mono text-gray-900 dark:text-gray-100">
                {stats.min?.toFixed(2)} – {stats.max?.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Mean:</span>
              <span className="font-mono text-gray-900 dark:text-gray-100">{stats.mean?.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Median:</span>
              <span className="font-mono text-gray-900 dark:text-gray-100">{stats.median?.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Std Dev:</span>
              <span className="font-mono text-gray-900 dark:text-gray-100">{stats.std?.toFixed(2)}</span>
            </div>
            {stats.outlier_count > 0 && (
              <div className="mt-2 text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5" />
                {stats.outlier_count} outlier{stats.outlier_count !== 1 ? 's' : ''} detected
              </div>
            )}
            {stats.null_percent > 0 && (
              <div className="text-xs text-gray-500">
                Nulls: {stats.null_percent.toFixed(1)}%
              </div>
            )}
          </div>
        )}

        {stats.type === 'categorical' && (
          <div className="text-sm space-y-1">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Unique Values:</span>
              <span className="font-mono text-gray-900 dark:text-gray-100">{stats.cardinality}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Entropy:</span>
              <span className="font-mono text-gray-900 dark:text-gray-100">{stats.entropy?.toFixed(2)}</span>
            </div>
            {stats.top_values && stats.top_values.length > 0 && (
              <div className="mt-2">
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Top Values:</div>
                {stats.top_values.slice(0, 3).map((v: any, i: number) => (
                  <div key={i} className="text-xs flex justify-between">
                    <span className="truncate max-w-[120px]">{v.value}</span>
                    <span className="text-gray-500">{v.percent.toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            )}
            {stats.null_percent > 0 && (
              <div className="text-xs text-gray-500">
                Nulls: {stats.null_percent.toFixed(1)}%
              </div>
            )}
          </div>
        )}

        {stats.type === 'temporal' && (
          <div className="text-sm space-y-1">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Date Range:</span>
              <span className="text-xs font-mono text-gray-900 dark:text-gray-100">
                {stats.range_days} days
              </span>
            </div>
            <div className="text-xs text-gray-600 dark:text-gray-400">
              {stats.min_date} → {stats.max_date}
            </div>
            {stats.trend && (
              <div className="mt-2 text-xs flex items-center gap-1">
                <TrendingUp className="w-3.5 h-3.5" />
                Trend: {stats.trend}
              </div>
            )}
            {stats.null_percent > 0 && (
              <div className="text-xs text-gray-500">
                Nulls: {stats.null_percent.toFixed(1)}%
              </div>
            )}
          </div>
        )}

        {stats.type === 'text' && (
          <div className="text-sm space-y-1">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Avg Length:</span>
              <span className="font-mono text-gray-900 dark:text-gray-100">{stats.avg_length?.toFixed(0)} chars</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Range:</span>
              <span className="font-mono text-gray-900 dark:text-gray-100">
                {stats.min_length} – {stats.max_length}
              </span>
            </div>
            {stats.null_percent > 0 && (
              <div className="text-xs text-gray-500">
                Nulls: {stats.null_percent.toFixed(1)}%
              </div>
            )}
          </div>
        )}
      </div>
    )
  }

  const renderCorrelations = () => {
    if (!response?.correlations || response.correlations.length === 0) {
      return <div className="text-sm text-gray-500">No significant correlations found</div>
    }

    return (
      <div className="grid grid-cols-1 gap-2">
        {response.correlations.map((corr, i) => {
          const strength = Math.abs(corr.r) > 0.8 ? 'strong' : Math.abs(corr.r) > 0.5 ? 'moderate' : 'weak'
          const color = Math.abs(corr.r) > 0.8 ? 'text-red-600 dark:text-red-400' :
                       Math.abs(corr.r) > 0.5 ? 'text-amber-600 dark:text-amber-400' :
                       'text-gray-600 dark:text-gray-400'

          return (
            <div key={i} className="flex items-center justify-between p-2 rounded bg-white/60 dark:bg-gray-800/40 border">
              <div className="flex-1 text-sm">
                <span className="font-medium">{corr.col1}</span>
                <span className="mx-2 text-gray-400">↔</span>
                <span className="font-medium">{corr.col2}</span>
              </div>
              <div className={`text-sm font-mono ${color}`}>
                r = {corr.r.toFixed(3)} ({strength})
              </div>
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-[1000px] max-w-[95vw] max-h-[90vh] overflow-auto rounded-xl shadow-xl border bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 sticky top-0 bg-white dark:bg-gray-900 z-10">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            <h3 className="text-base font-semibold">Pattern Discovery</h3>
            <span className="text-xs text-gray-500">⌘K P</span>
          </div>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-4">
          <div className="grid grid-cols-1 gap-3">
            {/* Data Source Picker */}
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

              <div className="grid grid-cols-3 gap-2">
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
                <input
                  value={tableName}
                  onChange={(e) => setTableName(e.target.value)}
                  placeholder="Table name (if session)"
                  className="rounded border px-3 py-2 bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-700 text-sm"
                />
              </div>
              <div className="mt-2">
                <input
                  type="number"
                  value={sampleRows}
                  onChange={(e) => setSampleRows(e.target.value)}
                  placeholder="Sample rows (default: 50000)"
                  min="100"
                  max="200000"
                  className="w-full rounded border px-3 py-2 bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-700 text-sm"
                />
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-2">
              <button
                onClick={onDiscover}
                disabled={loading || (!sessionId && !datasetId)}
                className="px-4 py-2 rounded-md text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
                <span>{loading ? 'Analyzing…' : 'Discover Patterns'}</span>
              </button>

              {response && (
                <>
                  <button
                    onClick={downloadJSON}
                    className="px-4 py-2 rounded-md text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 flex items-center gap-2"
                  >
                    <Download className="w-4 h-4" />
                    <span>Export JSON</span>
                  </button>
                  <button
                    onClick={downloadPDF}
                    className="px-4 py-2 rounded-md text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 flex items-center gap-2"
                  >
                    <Download className="w-4 h-4" />
                    <span>Export PDF</span>
                  </button>
                </>
              )}
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
                <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
              </div>
            )}

            {/* Empty State */}
            {!response && !loading && !error && (
              <div className="mt-4 text-center text-sm text-gray-500 dark:text-gray-400 py-8">
                <p>Enter a data source and click "Discover Patterns" to analyze your dataset.</p>
                <p className="mt-1">Get column statistics, correlations, outliers, and insights.</p>
              </div>
            )}

            {/* Results */}
            {response && (
              <div className="mt-3 space-y-4">
                {/* Metadata */}
                <div className="text-sm text-gray-600 dark:text-gray-400 flex items-center gap-4">
                  <span><strong>Rows:</strong> {response.metadata.total_rows.toLocaleString()}</span>
                  {response.metadata.sampled && <span className="text-amber-600 dark:text-amber-400">Sampled</span>}
                  <span><strong>Analysis Time:</strong> {response.metadata.total_time_ms.toFixed(0)} ms</span>
                </div>

                {/* Warnings */}
                {response.metadata.warnings && response.metadata.warnings.length > 0 && (
                  <div className="text-xs text-amber-600 dark:text-amber-400 space-y-1">
                    {response.metadata.warnings.map((w, i) => (
                      <div key={i}>• {w}</div>
                    ))}
                  </div>
                )}

                {/* Insights */}
                {response.insights && response.insights.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                      <TrendingUp className="w-4 h-4" />
                      Key Insights
                    </h4>
                    <div className="space-y-1">
                      {response.insights.map((insight, i) => (
                        <div key={i} className="text-sm text-gray-700 dark:text-gray-300 bg-blue-50/50 dark:bg-blue-900/10 p-2 rounded border border-blue-200 dark:border-blue-800">
                          • {insight}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Correlations */}
                {response.correlations && response.correlations.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold mb-2">Correlations</h4>
                    {renderCorrelations()}
                  </div>
                )}

                {/* Column Statistics */}
                <div>
                  <h4 className="text-sm font-semibold mb-2">
                    Column Statistics ({Object.keys(response.columns).length})
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {Object.entries(response.columns).map(([name, stats]) =>
                      renderColumnCard(name, stats)
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
