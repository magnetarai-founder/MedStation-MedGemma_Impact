import { useEffect, useState } from 'react'
import { X, Clock, Activity, AlertTriangle, FileText, Settings, User } from 'lucide-react'
import { authFetch } from '../lib/api'
import { showToast } from '../lib/toast'

interface AuditEntry {
  id: number
  user_id: string
  action: string
  resource: string | null
  resource_id: string | null
  ip_address: string | null
  user_agent: string | null
  timestamp: string
  details: Record<string, any> | null
}

interface SessionTimelineModalProps {
  sessionId: string
  sessionTitle?: string
  onClose: () => void
}

export function SessionTimelineModal({ sessionId, sessionTitle, onClose }: SessionTimelineModalProps) {
  const [logs, setLogs] = useState<AuditEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [, setTick] = useState(0) // Force re-render for timestamp updates

  useEffect(() => {
    fetchLogs()
  }, [sessionId])

  // Update relative timestamps every minute
  useEffect(() => {
    const interval = setInterval(() => {
      setTick(t => t + 1)
    }, 60000) // 60 seconds

    return () => clearInterval(interval)
  }, [])

  const fetchLogs = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await authFetch(`/api/v1/audit/sessions/${sessionId}?limit=100`)
      if (!response.ok) {
        throw new Error('Failed to fetch timeline')
      }

      const data = await response.json()
      setLogs(data.logs || [])
    } catch (err) {
      setError('Failed to load session timeline')
      showToast.error('Failed to load session timeline')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const getRelativeTime = (timestamp: string): string => {
    const now = new Date()
    const then = new Date(timestamp)
    const diffMs = now.getTime() - then.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    return `${diffDays}d ago`
  }

  const getEventIcon = (action: string) => {
    if (action.includes('token') || action.includes('limit')) return AlertTriangle
    if (action.includes('summarize')) return FileText
    if (action.includes('model')) return Settings
    if (action.includes('created')) return User
    return Activity
  }

  const getEventColor = (action: string) => {
    if (action.includes('token') || action.includes('limit')) return 'text-orange-600 dark:text-orange-400'
    if (action.includes('summarize')) return 'text-blue-600 dark:text-blue-400'
    if (action.includes('model')) return 'text-purple-600 dark:text-purple-400'
    if (action.includes('created')) return 'text-green-600 dark:text-green-400'
    return 'text-gray-600 dark:text-gray-400'
  }

  const getEventLabel = (action: string, details: Record<string, any> | null): string => {
    if (action === 'session.token.near_limit') {
      const pct = details?.percentage ? Math.round(details.percentage * 100) : 85
      return `Token usage warning (${pct}%)`
    }
    if (action === 'session.summarize.invoked') return 'Context summarization requested'
    if (action === 'session.model.updated') {
      const model = details?.model || 'unknown'
      return `Model changed to ${model}`
    }
    if (action === 'session.created') return 'Session created'
    if (action === 'session.renamed') return `Renamed to "${details?.title || 'untitled'}"`
    if (action === 'session.archived') return 'Session archived'
    if (action === 'session.restored') return 'Session restored'

    // Fallback: humanize action name
    return action.replace(/\./g, ' ').replace(/_/g, ' ')
  }

  return (
    <div className="fixed inset-0 bg-black/50 dark:bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              Session Timeline
            </h2>
            {sessionTitle && (
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                {sessionTitle}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {loading && (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
            </div>
          )}

          {error && (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <AlertTriangle size={48} className="mx-auto mb-4 text-red-500" />
                <p className="text-gray-600 dark:text-gray-400">{error}</p>
                <button
                  onClick={fetchLogs}
                  className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                >
                  Retry
                </button>
              </div>
            </div>
          )}

          {!loading && !error && logs.length === 0 && (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <Clock size={48} className="mx-auto mb-4 text-gray-400" />
                <p className="text-gray-600 dark:text-gray-400">No events recorded yet</p>
                <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">
                  Events will appear here as you use this session
                </p>
              </div>
            </div>
          )}

          {!loading && !error && logs.length > 0 && (
            <div className="space-y-3">
              {logs.map((log, index) => {
                const Icon = getEventIcon(log.action)
                const color = getEventColor(log.action)
                const label = getEventLabel(log.action, log.details)
                const relativeTime = getRelativeTime(log.timestamp)

                return (
                  <div
                    key={log.id || index}
                    className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                  >
                    <div className={`flex-shrink-0 mt-1 ${color}`}>
                      <Icon size={18} />
                    </div>

                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {label}
                      </p>
                      {log.details && Object.keys(log.details).length > 0 && (
                        <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                          {log.details.previous_model && (
                            <span>from {log.details.previous_model}</span>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="flex-shrink-0 text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
                      <Clock size={12} />
                      {relativeTime}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
