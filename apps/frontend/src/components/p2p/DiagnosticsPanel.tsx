import { useState } from 'react'
import { Loader2, X, AlertCircle, CheckCircle2, Activity, RefreshCw } from 'lucide-react'
import api from '@/lib/api'

interface DiagnosticsPanelProps {
  onClose: () => void
}

interface DiagnosticCheck {
  name: string
  ok: boolean
  message: string
  remediation?: string
}

interface DiagnosticsOverview {
  mdns_ok: boolean
  port_8000_open: boolean
  peer_count: number
  hints: string[]
}

export function DiagnosticsPanel({ onClose }: DiagnosticsPanelProps) {
  const [loading, setLoading] = useState(false)
  const [runningChecks, setRunningChecks] = useState(false)
  const [overview, setOverview] = useState<DiagnosticsOverview | null>(null)
  const [checks, setChecks] = useState<DiagnosticCheck[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loadOverview = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.get('/api/v1/p2p/diagnostics')
      setOverview(res.data)
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Failed to load diagnostics')
    } finally {
      setLoading(false)
    }
  }

  const runDetailedChecks = async () => {
    setRunningChecks(true)
    setError(null)
    try {
      const res = await api.post('/api/v1/p2p/diagnostics/run-checks')
      setChecks(res.data.checks)
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Failed to run checks')
    } finally {
      setRunningChecks(false)
    }
  }

  // Auto-load overview on mount
  useState(() => {
    loadOverview()
  })

  const renderOverviewCard = () => {
    if (!overview) return null

    return (
      <div className="bg-gray-50 dark:bg-gray-800/40 rounded-lg p-4 space-y-3">
        <h4 className="text-sm font-semibold flex items-center gap-2">
          <Activity className="w-4 h-4" />
          Quick Status
        </h4>

        <div className="grid grid-cols-3 gap-3">
          {/* mDNS */}
          <div className="bg-white dark:bg-gray-900/40 rounded p-3 border">
            <div className="flex items-center gap-2 mb-1">
              {overview.mdns_ok ? (
                <CheckCircle2 className="w-4 h-4 text-green-600 dark:text-green-400" />
              ) : (
                <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400" />
              )}
              <span className="text-xs font-medium text-gray-700 dark:text-gray-300">mDNS</span>
            </div>
            <div className="text-xs text-gray-500">
              {overview.mdns_ok ? 'Available' : 'Unavailable'}
            </div>
          </div>

          {/* Port 8000 */}
          <div className="bg-white dark:bg-gray-900/40 rounded p-3 border">
            <div className="flex items-center gap-2 mb-1">
              {overview.port_8000_open ? (
                <CheckCircle2 className="w-4 h-4 text-green-600 dark:text-green-400" />
              ) : (
                <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400" />
              )}
              <span className="text-xs font-medium text-gray-700 dark:text-gray-300">Port 8000</span>
            </div>
            <div className="text-xs text-gray-500">
              {overview.port_8000_open ? 'Open' : 'Closed'}
            </div>
          </div>

          {/* Peers */}
          <div className="bg-white dark:bg-gray-900/40 rounded p-3 border">
            <div className="flex items-center gap-2 mb-1">
              {overview.peer_count > 0 ? (
                <CheckCircle2 className="w-4 h-4 text-green-600 dark:text-green-400" />
              ) : (
                <AlertCircle className="w-4 h-4 text-gray-400 dark:text-gray-500" />
              )}
              <span className="text-xs font-medium text-gray-700 dark:text-gray-300">Peers</span>
            </div>
            <div className="text-xs text-gray-500">
              {overview.peer_count} discovered
            </div>
          </div>
        </div>

        {/* Hints */}
        {overview.hints && overview.hints.length > 0 && (
          <div className="mt-3 space-y-1">
            <div className="text-xs font-medium text-gray-700 dark:text-gray-300">Hints:</div>
            {overview.hints.map((hint, i) => (
              <div
                key={i}
                className={`text-xs p-2 rounded ${
                  hint.includes('✅')
                    ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
                    : 'bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300'
                }`}
              >
                • {hint}
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  const renderDetailedChecks = () => {
    if (!checks) return null

    return (
      <div className="space-y-2">
        <h4 className="text-sm font-semibold">Detailed Checks</h4>
        {checks.map((check, i) => (
          <div
            key={i}
            className={`border rounded-lg p-3 ${
              check.ok
                ? 'bg-green-50 dark:bg-green-900/10 border-green-200 dark:border-green-800'
                : 'bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-800'
            }`}
          >
            <div className="flex items-start gap-2">
              {check.ok ? (
                <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
              ) : (
                <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{check.name}</span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded ${
                      check.ok
                        ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200'
                        : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200'
                    }`}
                  >
                    {check.ok ? 'PASS' : 'FAIL'}
                  </span>
                </div>
                <div className="text-sm text-gray-700 dark:text-gray-300 mt-1">{check.message}</div>
                {check.remediation && (
                  <div className="mt-2 text-xs text-gray-600 dark:text-gray-400 bg-white/60 dark:bg-gray-800/60 p-2 rounded">
                    <strong>Fix:</strong> {check.remediation}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-[700px] max-w-[95vw] max-h-[90vh] overflow-auto rounded-xl shadow-xl border bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 sticky top-0 bg-white dark:bg-gray-900 z-10">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5" />
            <h3 className="text-base font-semibold">P2P Diagnostics</h3>
          </div>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-4 space-y-4">
          {/* Action Buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={loadOverview}
              disabled={loading}
              className="px-4 py-2 rounded-md text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 flex items-center gap-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              <span>{loading ? 'Loading…' : 'Refresh Overview'}</span>
            </button>

            <button
              onClick={runDetailedChecks}
              disabled={runningChecks}
              className="px-4 py-2 rounded-md text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-50 flex items-center gap-2"
            >
              {runningChecks ? <Loader2 className="w-4 h-4 animate-spin" /> : <Activity className="w-4 h-4" />}
              <span>{runningChecks ? 'Running…' : 'Run Detailed Checks'}</span>
            </button>
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
              <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
            </div>
          )}

          {/* Overview */}
          {overview && renderOverviewCard()}

          {/* Detailed Checks */}
          {checks && renderDetailedChecks()}

          {/* Empty State */}
          {!overview && !checks && !loading && !runningChecks && !error && (
            <div className="text-center text-sm text-gray-500 dark:text-gray-400 py-8">
              <p>Click "Refresh Overview" to check P2P status</p>
              <p className="mt-1">or "Run Detailed Checks" for in-depth diagnostics</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
