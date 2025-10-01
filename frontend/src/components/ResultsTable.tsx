import { useSessionStore } from '@/stores/sessionStore'
import { useSettingsStore } from '@/stores/settingsStore'
import { Download, Table, Trash2 } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function ResultsTable() {
  const { sessionId, currentQuery, isExecuting, setCurrentQuery, exportFormat, setExportFormat } = useSessionStore()
  const { previewRowCount } = useSettingsStore()

  const exportMutation = useMutation({
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
    onSuccess: () => {
      // Export completed successfully
    },
    onError: (error) => {
      console.error('Export failed:', error)
    },
  })

  // Defensive: coerce columns/rows for rendering to avoid runtime errors
  const columns = Array.isArray(currentQuery?.columns) ? currentQuery!.columns : []
  const allRows = Array.isArray(currentQuery?.preview) ? currentQuery!.preview : []
  
  // Limit rows displayed to prevent UI freezing with large datasets
  const MAX_DISPLAY_ROWS = 500
  const rows = allRows.slice(0, MAX_DISPLAY_ROWS)
  const hasMoreRows = allRows.length > MAX_DISPLAY_ROWS

  return (
    <div className="h-full flex flex-col glass-panel">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 dark:border-gray-700/30">
        <div className="flex items-center space-x-4">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            Results {currentQuery ? `(${(currentQuery.row_count ?? rows.length).toLocaleString()} rows)` : ''}
          </h3>
          <span className="text-xs text-gray-500">
            {currentQuery ? `Query completed in ${currentQuery.execution_time_ms.toFixed(0)}ms` : 'No preview yet'}
          </span>
        </div>
        
        <div className="flex items-center space-x-2">
          {/* Export format dropdown */}
          <select
            value={exportFormat}
            onChange={(e) => setExportFormat(e.target.value as 'excel' | 'csv' | 'json' | 'parquet')}
            className="px-2 py-1 text-xs rounded border border-gray-200 bg-white hover:bg-gray-50 dark:bg-gray-900 dark:border-gray-700 dark:hover:bg-gray-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="excel">Excel</option>
            <option value="csv">CSV</option>
            <option value="json">JSON</option>
            <option value="parquet">Parquet</option>
          </select>

          {/* Download button */}
          <button
            onClick={() => {
              exportMutation.mutate(exportFormat)
              // Remember the format after successful download
            }}
            disabled={exportMutation.isPending || !currentQuery}
            className="flex items-center space-x-1 px-2 py-1 text-xs rounded bg-blue-500 text-white hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed dark:bg-blue-600 dark:hover:bg-blue-700 dark:disabled:bg-gray-700"
            title="Download results"
          >
            <Download className="w-3 h-3" />
            <span>Download</span>
          </button>

          {/* Clear results */}
          <button
            onClick={() => { if (window.confirm('Clear current results preview?')) { setCurrentQuery(null) } }}
            className="flex items-center space-x-1 px-2 py-1 text-xs rounded hover:bg-gray-100 dark:hover:bg-gray-800"
            title="Clear results"
          >
            <Trash2 className="w-3 h-3" />
          </button>
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
              <p>Click Preview to fetch the first {previewRowCount} rows</p>
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
                  className="px-4 py-2 text-left font-medium text-gray-700 dark:text-gray-300"
                >
                  {col}
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
                {columns.map((col) => (
                  <td key={col} className="px-4 py-2 text-gray-900 dark:text-gray-100">
                    {row[col] === null ? (
                      <span className="text-gray-400 italic">null</span>
                    ) : (
                      String(row[col])
                    )}
                  </td>
                ))}
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
