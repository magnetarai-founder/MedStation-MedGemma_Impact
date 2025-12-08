import { useState } from 'react'
import { useJsonStore } from '@/stores/jsonStore'
import { useSessionStore } from '@/stores/sessionStore'
import { Download, Table, Trash2 } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function JsonResultsTable() {
  const { sessionId } = useSessionStore()
  const { conversionResult, setConversionResult } = useJsonStore()
  const previewRowCount = 100 // Hardcoded preview limit
  const [exportFormat, setExportFormat] = useState<'excel' | 'csv' | 'tsv' | 'parquet'>('excel')

  const exportMutation = useMutation({
    mutationKey: ['export-json-results', sessionId],
    mutationFn: async (format: 'excel' | 'csv' | 'tsv' | 'parquet') => {
      if (!sessionId || !conversionResult) throw new Error('No data to export')

      // Use the main export endpoint with json_ query_id
      const queryId = `json_${Date.now()}`
      const blob = await api.exportResults(sessionId, queryId, format)

      // Download the file
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `export_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.${format === 'excel' ? 'xlsx' : format === 'tsv' ? 'tsv' : format}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    },
  })

  // Defensive: coerce columns/rows for rendering to avoid runtime errors
  const columns = Array.isArray(conversionResult?.columns) ? conversionResult!.columns : []
  const allRows = Array.isArray(conversionResult?.preview) ? conversionResult!.preview : []
  // Limit preview rows based on settings
  const rows = allRows.slice(0, previewRowCount)

  return (
    <div className="h-full flex flex-col glass-panel">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 dark:border-gray-700/30">
        <div className="flex items-center space-x-4">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            Results {conversionResult ? `(${(conversionResult.total_rows ?? rows.length).toLocaleString()} rows)` : ''}
          </h3>
        </div>
        
        <div className="flex items-center space-x-2">
          {/* Export format dropdown */}
          <select
            value={exportFormat}
            onChange={(e) => setExportFormat(e.target.value as 'excel' | 'csv' | 'tsv' | 'parquet')}
            className="px-2 py-1 text-xs rounded border border-gray-200 bg-white hover:bg-gray-50 dark:bg-gray-900 dark:border-gray-700 dark:hover:bg-gray-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="excel">Excel</option>
            <option value="csv">CSV</option>
            <option value="tsv">TSV</option>
            <option value="parquet">Parquet</option>
          </select>

          {/* Download button */}
          <button
            onClick={() => exportMutation.mutate(exportFormat)}
            disabled={exportMutation.isPending || !conversionResult || conversionResult.is_preview_only}
            className="flex items-center space-x-1 px-2 py-1 text-xs rounded bg-blue-500 text-white hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed dark:bg-blue-600 dark:hover:bg-blue-700 dark:disabled:bg-gray-700"
            title={conversionResult?.is_preview_only ? "Run full conversion to download" : "Download results"}
          >
            <Download className="w-3 h-3" />
            <span>Download</span>
          </button>

          {/* Clear results */}
          <button
            onClick={() => { if (window.confirm('Clear current results?')) { setConversionResult(null) } }}
            className="flex items-center space-x-1 px-2 py-1 text-xs rounded hover:bg-gray-100 dark:hover:bg-gray-800"
            title="Clear results"
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      </div>
      
      <div className="flex-1 overflow-auto relative">
        {!conversionResult && (
          <div className="flex h-full items-center justify-center">
            <div className="text-center text-gray-500">
              <Table className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>Click Preview to fetch the first {previewRowCount} rows</p>
            </div>
          </div>
        )}

        {conversionResult && (
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
        
        {conversionResult && rows.length === 0 && (
          <div className="p-8 text-center text-sm text-gray-500">
            No rows in conversion result
          </div>
        )}
      </div>
    </div>
  )
}