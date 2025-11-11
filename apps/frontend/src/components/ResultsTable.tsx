import { useSessionStore } from '@/stores/sessionStore'
import { useSettingsStore } from '@/stores/settingsStore'
import { useEditorStore } from '@/stores/editorStore'
import { useNavigationStore } from '@/stores/navigationStore'
import { useChatStore } from '@/stores/chatStore'
import { Download, Table, Trash2, MessageSquare, Loader2 } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import toast from 'react-hot-toast'
import { shallow } from 'zustand/shallow'  // MED-03: Prevent unnecessary re-renders

export function ResultsTable() {
  // MED-03: Use shallow selectors for multi-field access
  const { sessionId, currentQuery, currentSql, isExecuting, setCurrentQuery, exportFormat, setExportFormat } = useSessionStore(
    (state) => ({
      sessionId: state.sessionId,
      currentQuery: state.currentQuery,
      currentSql: state.currentSql,
      isExecuting: state.isExecuting,
      setCurrentQuery: state.setCurrentQuery,
      exportFormat: state.exportFormat,
      setExportFormat: state.setExportFormat,
    }),
    shallow
  )
  const { contentType, hasExecuted } = useEditorStore(
    (state) => ({ contentType: state.contentType, hasExecuted: state.hasExecuted }),
    shallow
  )
  const setActiveTab = useNavigationStore((state) => state.setActiveTab)  // Single field - no shallow needed
  const setActiveChat = useChatStore((state) => state.setActiveChat)  // Single field - no shallow needed

  const exportMutation = useMutation({
    mutationKey: ['export-results', sessionId, currentQuery?.query_id],
    mutationFn: async (format: 'excel' | 'csv' | 'parquet' | 'json') => {
      if (!sessionId || !currentQuery) throw new Error('No data to export')
      const blob = await api.exportResults(sessionId, currentQuery.query_id, format)

      // Download the file
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `neutron_export_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.${format === 'excel' ? 'xlsx' : format}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)

      // Remember the format after successful download (it's already saved via setExportFormat onChange)
    },
    onSuccess: (_, format) => {
      toast.success(`Successfully exported to ${format.toUpperCase()}`)
    },
    onError: (error) => {
      console.error('Export failed:', error)
      toast.error('Failed to export results')
    },
  })

  const exportToAIChatMutation = useMutation({
    mutationKey: ['export-to-ai-chat', sessionId, currentQuery?.query_id],
    mutationFn: async () => {
      if (!sessionId || !currentQuery) throw new Error('No data to export')

      const response = await fetch(`/api/v1/chat/data/export-to-chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          query_id: currentQuery.query_id,
          query: currentSql || 'SELECT * FROM excel_file',
          results: currentQuery.preview || []
        })
      })

      if (!response.ok) throw new Error('Failed to export to AI chat')
      return await response.json()
    },
    onSuccess: (data) => {
      // Navigate to chat tab and activate the new session
      setActiveChat(data.chat_id)
      setActiveTab('chat')
      const rowCount = currentQuery?.row_count || currentQuery?.preview?.length || 0
      toast.success(`${rowCount.toLocaleString()} rows exported for AI analysis!`)
      console.log('Exported to chat session:', data.chat_id)
    },
    onError: (error) => {
      console.error('Export to AI chat failed:', error)
      toast.error('Failed to export to AI Chat')
    },
  })

  // Defensive: coerce columns/rows for rendering to avoid runtime errors
  const columns = Array.isArray(currentQuery?.columns) ? currentQuery!.columns : []
  const allRows = Array.isArray(currentQuery?.preview) ? currentQuery!.preview : []

  // Limit rows displayed to prevent UI freezing with large datasets
  const MAX_DISPLAY_ROWS = 500
  const rows = allRows.slice(0, MAX_DISPLAY_ROWS)
  const hasMoreRows = allRows.length > MAX_DISPLAY_ROWS

  // Dynamic format options based on content type
  const formatOptions = contentType === 'json'
    ? [
        { value: 'excel', label: 'Excel' },
        { value: 'csv', label: 'CSV' },
        { value: 'tsv', label: 'TSV' },
        { value: 'parquet', label: 'Parquet' },
      ]
    : [
        { value: 'excel', label: 'Excel' },
        { value: 'csv', label: 'CSV' },
        { value: 'parquet', label: 'Parquet' },
        { value: 'json', label: 'JSON' },
      ]

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center px-2 py-2 border-b-2 border-gray-600 dark:border-gray-400">
        {/* Grouped pills design - left aligned */}
        <div className="flex items-center gap-3">
          {/* Group 1: Dropdown + Download */}
          <div className="flex items-center px-1.5 py-0.5 rounded-md bg-gray-100/50 dark:bg-gray-800/50 gap-1">
            {/* Export format dropdown */}
            <select
              value={exportFormat}
              onChange={(e) => setExportFormat(e.target.value as 'excel' | 'csv' | 'json' | 'parquet')}
              disabled={!hasExecuted || !currentQuery}
              className="px-2 py-0.5 text-xs rounded border-0 bg-transparent hover:bg-gray-200 dark:hover:bg-gray-700 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed text-gray-700 dark:text-gray-300"
            >
              {formatOptions.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>

            {/* Download button */}
            <button
              onClick={() => {
                exportMutation.mutate(exportFormat)
              }}
              disabled={exportMutation.isPending || !currentQuery || !hasExecuted || currentQuery.is_preview_only}
              className={`p-1 rounded ${
                exportMutation.isPending || !currentQuery || !hasExecuted || currentQuery.is_preview_only
                  ? 'opacity-50 cursor-not-allowed'
                  : 'hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
              title={currentQuery?.is_preview_only ? "Run full conversion to download" : "Download results"}
            >
              {exportMutation.isPending ? (
                <Loader2 className="w-4 h-4 text-gray-700 dark:text-gray-300 animate-spin" />
              ) : (
                <Download className="w-4 h-4 text-gray-700 dark:text-gray-300" />
              )}
            </button>
          </div>

          {/* Group 2: Export to AI Chat */}
          <div className="flex items-center px-1.5 py-0.5 rounded-md bg-gray-100/50 dark:bg-gray-800/50">
            <button
              onClick={() => exportToAIChatMutation.mutate()}
              disabled={exportToAIChatMutation.isPending || !currentQuery || !hasExecuted}
              className={`flex items-center gap-1.5 px-2 py-0.5 text-xs rounded ${
                exportToAIChatMutation.isPending || !currentQuery || !hasExecuted
                  ? 'opacity-50 cursor-not-allowed'
                  : 'hover:bg-primary-100 dark:hover:bg-primary-900/30 text-primary-700 dark:text-primary-400'
              }`}
              title="Analyze query results with AI"
            >
              {exportToAIChatMutation.isPending ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <MessageSquare className="w-3.5 h-3.5" />
              )}
              <span>{exportToAIChatMutation.isPending ? 'Exporting...' : 'Analyze with AI'}</span>
            </button>
          </div>

          {/* Group 3: Trash */}
          <div className="flex items-center px-1.5 py-0.5 rounded-md bg-gray-100/50 dark:bg-gray-800/50">
            {/* Clear results */}
            <button
              onClick={() => { if (window.confirm('Clear current results preview?')) { setCurrentQuery(null) } }}
              disabled={!currentQuery}
              className={`p-1 rounded ${
                !currentQuery
                  ? 'opacity-50 cursor-not-allowed'
                  : 'hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
              title={!currentQuery ? 'No results to clear' : 'Clear results'}
            >
              <Trash2 className="w-4 h-4 text-gray-700 dark:text-gray-300" />
            </button>
          </div>
        </div>
      </div>
      
      <div className="flex-1 overflow-auto relative">
        {isExecuting && (
          <div className="absolute inset-0 bg-black/5 dark:bg-white/5 flex items-center justify-center z-10">
            <div>
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600 mx-auto"></div>
              <p className="mt-2 text-xs text-gray-600 dark:text-gray-400 text-center">Loading preview...</p>
            </div>
          </div>
        )}

        {!currentQuery && !isExecuting && (
          <div className="flex h-full items-center justify-center">
            <div className="text-center text-gray-500">
              <Table className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>Execute a query to view results</p>
            </div>
          </div>
        )}

        {currentQuery && (
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
            <tr>
              {columns.map((col) => (
                <th
                  key={col}
                  className="px-4 py-2 text-left font-medium text-gray-700 dark:text-gray-300 whitespace-nowrap"
                  style={{ maxWidth: '300px' }}
                >
                  <div className="truncate" title={col}>
                    {col}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr
                key={idx}
                className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-900"
              >
                {columns.map((col) => {
                  const value = row[col]
                  const displayValue = value === null ? 'null' : String(value)
                  return (
                    <td
                      key={col}
                      className="px-4 py-2 text-gray-900 dark:text-gray-100"
                      style={{ maxWidth: '300px' }}
                    >
                      <div
                        className="truncate"
                        title={displayValue}
                      >
                        {value === null ? (
                          <span className="text-gray-400 italic">null</span>
                        ) : (
                          displayValue
                        )}
                      </div>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
        )}
        
        {currentQuery && (currentQuery.has_more || hasMoreRows) && rows.length > 0 && (
          <div className="p-4 text-center text-sm text-gray-500">
            {hasMoreRows 
              ? `Showing first ${rows.length} rows (UI display limit) of ${allRows.length} in preview`
              : `Showing first ${rows.length} rows of ${(currentQuery.row_count ?? rows.length).toLocaleString()} total`
            }
          </div>
        )}
        {currentQuery && rows.length === 0 && !isExecuting && (
          <div className="p-8 text-center text-sm text-gray-500">
            No rows returned in preview.
          </div>
        )}
      </div>
    </div>
  )
}
