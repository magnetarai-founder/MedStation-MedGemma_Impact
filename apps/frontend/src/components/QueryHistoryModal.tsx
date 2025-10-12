import { useState, useEffect } from 'react'
import { X, Play, Clock, Trash2, Search } from 'lucide-react'
import { api } from '../lib/api'
import { useSessionStore } from '../stores/sessionStore'

interface QueryHistoryItem {
  id: string
  query: string
  timestamp: string
  executionTime?: number
  rowCount?: number
  status: 'success' | 'error'
}

interface QueryHistoryModalProps {
  isOpen: boolean
  onClose: () => void
  onRunQuery?: (query: string) => void
}

export function QueryHistoryModal({ isOpen, onClose, onRunQuery }: QueryHistoryModalProps) {
  const { sessionId } = useSessionStore()
  const [history, setHistory] = useState<QueryHistoryItem[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (isOpen && sessionId) {
      loadHistory()
    }
  }, [isOpen, sessionId])

  const loadHistory = async () => {
    setIsLoading(true)
    try {
      const response = await api.getQueryHistory(sessionId)
      setHistory(response.history || [])
    } catch (error) {
      console.error('Failed to load query history:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleRunQuery = (query: string) => {
    if (onRunQuery) {
      onRunQuery(query)
      onClose()
    }
  }

  const handleDeleteQuery = async (id: string) => {
    try {
      await api.deleteQueryFromHistory(sessionId, id)
      setHistory(history.filter((item) => item.id !== id))
    } catch (error) {
      console.error('Failed to delete query:', error)
    }
  }

  const filteredHistory = history.filter((item) =>
    item.query.toLowerCase().includes(searchTerm.toLowerCase())
  )

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose}></div>

      {/* Modal */}
      <div className="relative w-full max-w-4xl mx-4 max-h-[80vh] glass rounded-2xl border border-white/30 dark:border-gray-700/40 shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/20 dark:border-gray-700/40">
          <div className="flex items-center gap-3">
            <Clock size={24} className="text-primary-600 dark:text-primary-400" />
            <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Query History</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/60 dark:hover:bg-gray-700/60 rounded-lg transition-all text-gray-600 dark:text-gray-400"
          >
            <X size={20} />
          </button>
        </div>

        {/* Search */}
        <div className="p-4 border-b border-white/20 dark:border-gray-700/40">
          <div className="relative">
            <Search
              size={18}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500"
            />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search queries..."
              className="w-full pl-10 pr-4 py-2 rounded-lg bg-white/60 dark:bg-gray-800/60 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 border border-gray-300/50 dark:border-gray-600/50 focus:outline-none focus:ring-2 focus:ring-primary-500/50 transition-all"
            />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {isLoading ? (
            <div className="flex items-center justify-center h-48">
              <div className="text-gray-500 dark:text-gray-400">Loading history...</div>
            </div>
          ) : filteredHistory.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-48 text-gray-500 dark:text-gray-400">
              <Clock size={48} className="mb-4 opacity-30" />
              <p className="text-lg">No query history yet</p>
              <p className="text-sm mt-2">Run some queries to see them here</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredHistory.map((item) => (
                <div
                  key={item.id}
                  className="p-4 rounded-lg bg-white/40 dark:bg-gray-800/40 border border-gray-200/50 dark:border-gray-700/50 hover:bg-white/60 dark:hover:bg-gray-800/60 transition-all group"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      {/* Query */}
                      <pre className="text-sm font-mono text-gray-900 dark:text-gray-100 whitespace-pre-wrap break-words mb-2">
                        {item.query}
                      </pre>

                      {/* Metadata */}
                      <div className="flex items-center gap-4 text-xs text-gray-600 dark:text-gray-400">
                        <span className="flex items-center gap-1">
                          <Clock size={12} />
                          {new Date(item.timestamp).toLocaleString()}
                        </span>
                        {item.executionTime && (
                          <span>{item.executionTime.toFixed(2)}ms</span>
                        )}
                        {item.rowCount !== undefined && (
                          <span>{item.rowCount} rows</span>
                        )}
                        <span
                          className={`px-2 py-0.5 rounded ${
                            item.status === 'success'
                              ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                              : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                          }`}
                        >
                          {item.status}
                        </span>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={() => handleRunQuery(item.query)}
                        className="p-2 hover:bg-primary-500/20 rounded-lg transition-all text-primary-600 dark:text-primary-400"
                        title="Run query"
                      >
                        <Play size={16} />
                      </button>
                      <button
                        onClick={() => handleDeleteQuery(item.id)}
                        className="p-2 hover:bg-red-500/20 rounded-lg transition-all text-red-600 dark:text-red-400"
                        title="Delete"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t border-white/20 dark:border-gray-700/40">
          <div className="text-sm text-gray-600 dark:text-gray-400">
            {filteredHistory.length} {filteredHistory.length === 1 ? 'query' : 'queries'}
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-white font-medium transition-all"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
