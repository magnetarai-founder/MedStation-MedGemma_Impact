import { useState } from 'react'
import { Clock, FileText, Trash2, Save, Filter } from 'lucide-react'
import { useHistoryStore, HistoryItem } from '@/stores/historyStore'
import { useQueriesStore } from '@/stores/queriesStore'
import { useNavigationStore } from '@/stores/navigationStore'
import { useSessionStore } from '@/stores/sessionStore'

export function QueryHistoryList() {
  const { history, clearHistory, deleteHistoryItem } = useHistoryStore()
  const { addQuery } = useQueriesStore()
  const { setActiveTab } = useNavigationStore()
  const { currentFile } = useSessionStore()
  const [filterType, setFilterType] = useState<'all' | 'sql' | 'json'>('all')
  const [filterDate, setFilterDate] = useState<'all' | 'today' | 'week'>('all')

  const formatTimestamp = (timestamp: number) => {
    const now = Date.now()
    const diff = now - timestamp
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)

    if (minutes < 1) return 'Just now'
    if (minutes < 60) return `${minutes}m ago`
    if (hours < 24) return `${hours}h ago`
    return `${days}d ago`
  }

  const filterHistory = () => {
    let filtered = history

    // Filter by type
    if (filterType !== 'all') {
      filtered = filtered.filter(item => item.type === filterType)
    }

    // Filter by date
    if (filterDate !== 'all') {
      const now = Date.now()
      const oneDayAgo = now - 86400000
      const oneWeekAgo = now - 604800000

      filtered = filtered.filter(item => {
        if (filterDate === 'today') return item.timestamp >= oneDayAgo
        if (filterDate === 'week') return item.timestamp >= oneWeekAgo
        return true
      })
    }

    return filtered
  }

  const handleHistoryClick = (item: HistoryItem) => {
    // Check if Excel file is loaded for SQL queries
    if (item.type === 'sql' && !currentFile) {
      alert('Please load an Excel or CSV file first')
      return
    }

    // Load query into editor
    window.dispatchEvent(new CustomEvent('code-file-loaded', {
      detail: { content: item.query, type: item.type }
    }))

    // Switch to editor tab
    setActiveTab('editor')
  }

  const handleSaveToQueries = (item: HistoryItem) => {
    const name = prompt('Save query as:', `Query ${new Date(item.timestamp).toLocaleString()}`)
    if (name?.trim()) {
      addQuery(name.trim(), item.query, item.type, null)
    }
  }

  const filteredHistory = filterHistory()

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-800">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold">History</h3>
          <button
            onClick={() => {
              if (window.confirm('Clear all query history?')) {
                clearHistory()
              }
            }}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded text-red-600"
            title="Clear History"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>

        {/* Filters */}
        <div className="flex items-center space-x-2 text-xs">
          <Filter className="w-3 h-3 text-gray-400" />
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value as any)}
            className="px-2 py-1 rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900"
          >
            <option value="all">All Types</option>
            <option value="sql">SQL</option>
            <option value="json">JSON</option>
          </select>
          <select
            value={filterDate}
            onChange={(e) => setFilterDate(e.target.value as any)}
            className="px-2 py-1 rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900"
          >
            <option value="all">All Time</option>
            <option value="today">Today</option>
            <option value="week">This Week</option>
          </select>
        </div>
      </div>

      {/* History List */}
      <div className="flex-1 overflow-auto">
        {filteredHistory.length === 0 ? (
          <div className="p-4 text-center text-sm text-gray-500">
            {history.length === 0 ? 'No query history yet' : 'No queries match filters'}
          </div>
        ) : (
          <div className="divide-y divide-gray-200 dark:divide-gray-800">
            {filteredHistory.map(item => (
              <div
                key={item.id}
                className="px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer group"
                onClick={() => handleHistoryClick(item)}
              >
                <div className="flex items-start justify-between mb-1">
                  <div className="flex items-center space-x-2">
                    <Clock className="w-3 h-3 text-gray-400" />
                    <span className="text-xs text-gray-500">{formatTimestamp(item.timestamp)}</span>
                    <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 uppercase font-medium">
                      {item.type}
                    </span>
                  </div>
                  <div className="flex space-x-1 opacity-0 group-hover:opacity-100">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleSaveToQueries(item)
                      }}
                      className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                      title="Save to Queries"
                    >
                      <Save className="w-3 h-3" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        if (window.confirm('Delete this history item?')) {
                          deleteHistoryItem(item.id)
                        }
                      }}
                      className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-red-600"
                      title="Delete"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
                <div className="text-sm font-mono text-gray-700 dark:text-gray-300 line-clamp-2">
                  {item.query}
                </div>
                {(item.executionTime || item.rowCount) && (
                  <div className="flex items-center space-x-3 mt-1 text-xs text-gray-400">
                    {item.executionTime && <span>{item.executionTime}ms</span>}
                    {item.rowCount !== undefined && <span>{item.rowCount.toLocaleString()} rows</span>}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-gray-200 dark:border-gray-800 text-xs text-gray-500">
        {filteredHistory.length} of {history.length} queries
      </div>
    </div>
  )
}
