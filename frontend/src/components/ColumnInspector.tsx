import { Database, PlusCircle } from 'lucide-react'
import { useState } from 'react'
import { useSessionStore } from '@/stores/sessionStore'
import { useJsonStore } from '@/stores/jsonStore'
import { useNavigationStore } from '@/stores/navigationStore'

export function ColumnInspector() {
  const { currentFile } = useSessionStore()
  const { jsonFileData } = useJsonStore()
  const { activeTab } = useNavigationStore()
  const [lastInserted, setLastInserted] = useState<string | null>(null)

  // Use SQL file data or JSON file data based on active tab
  const fileData = activeTab === 'sql' ? currentFile : jsonFileData
  
  if (!fileData) {
    return (
      <div className="p-4 text-center text-gray-500">
        <Database className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No file loaded</p>
      </div>
    )
  }

  const insertToEditor = (columnName: string) => {
    if (activeTab === 'sql') {
      // Insert as a quoted identifier for SQL
      const quoted = '"' + String(columnName).replace(/"/g, '""') + '"'
      try {
        window.dispatchEvent(new CustomEvent('insert-sql', { detail: quoted }))
        setLastInserted(columnName)
        setTimeout(() => setLastInserted(null), 1200)
      } catch {
        // no-op
      }
    } else {
      // For JSON, insert the column path
      try {
        window.dispatchEvent(new CustomEvent('insert-json-path', { detail: columnName }))
        setLastInserted(columnName)
        setTimeout(() => setLastInserted(null), 1200)
      } catch {
        // no-op
      }
    }
  }

  // Get columns based on the active tab
  const columns = activeTab === 'sql' 
    ? (currentFile?.columns || [])
    : (jsonFileData?.columns || [])
  
  const columnCount = activeTab === 'sql'
    ? currentFile?.column_count
    : jsonFileData?.columns?.length || 0

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 pt-4 pb-2">
        <h3 className="text-sm font-semibold">
          {activeTab === 'sql' ? 'Columns' : 'Column Preview'} ({columnCount})
        </h3>
      </div>
      <div className="flex-1 overflow-auto px-2 pb-4">
        <ul className="text-sm divide-y divide-gray-200 dark:divide-gray-800 rounded-md bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800">
          {columns.map((col: any) => {
            // Handle both SQL columns (objects) and JSON columns (strings)
            const columnName = typeof col === 'string' ? col : col.original_name
            
            if (activeTab === 'json') {
              // For JSON tab - just show as preview, not clickable
              return (
                <li
                  key={columnName}
                  className="flex items-center justify-between px-3 py-2"
                  title={columnName}
                >
                  <span className="truncate text-gray-700 dark:text-gray-300">{columnName}</span>
                </li>
              )
            }
            
            // For SQL tab - keep the original clickable behavior
            return (
              <li
                key={columnName}
                className="flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800"
                onClick={() => insertToEditor(columnName)}
                title={columnName}
              >
                <span className="truncate">{columnName}</span>
                <button
                  onClick={(e) => { e.stopPropagation(); insertToEditor(columnName) }}
                  className="ml-3 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
                  title="Insert into editor"
                >
                  <PlusCircle className={`w-4 h-4 ${lastInserted === columnName ? 'text-green-600' : 'text-gray-400'}`} />
                </button>
              </li>
            )
          })}
        </ul>
      </div>
      <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-800 text-xs text-gray-500">
        {activeTab === 'sql' ? 'Showing Excel headers exactly as loaded' : 'Preview of flattened JSON paths'}
      </div>
    </div>
  )
}