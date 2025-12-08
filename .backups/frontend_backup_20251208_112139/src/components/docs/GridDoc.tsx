import { useEffect, useState, useRef } from 'react'
import { Wifi, WifiOff, Users, Loader2, Plus, Trash2, Download, Upload, History, RotateCcw } from 'lucide-react'
import * as Y from 'yjs'
import { getYDoc, destroyYDoc, getYArray } from '@/lib/collab/yDoc'
import { createWebSocketProvider, destroyWebSocketProvider } from '@/lib/collab/yProvider'

interface Snapshot {
  id: string
  size_bytes: number
  modified_ts: number
}

interface GridDocProps {
  docId: string
  token: string // JWT token
  className?: string
}

interface CellPosition {
  row: number
  col: number
}

export function GridDoc({ docId, token, className = '' }: GridDocProps) {
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'synced'>(
    'disconnected'
  )
  const [rows, setRows] = useState<Y.Map<any>[]>([])
  const [columns, setColumns] = useState<string[]>(['A', 'B', 'C', 'D', 'E'])
  const [activeCell, setActiveCell] = useState<CellPosition | null>(null)
  const [editingCell, setEditingCell] = useState<CellPosition | null>(null)
  const [cellValue, setCellValue] = useState('')
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [showHistory, setShowHistory] = useState(false)
  const [loadingSnapshots, setLoadingSnapshots] = useState(false)
  const [restoringSnapshot, setRestoringSnapshot] = useState(false)

  const ydocRef = useRef<Y.Doc | null>(null)
  const yarrayRef = useRef<Y.Array<Y.Map<any>> | null>(null)
  const providerRef = useRef<any>(null)

  // Initialize Yjs on mount
  useEffect(() => {
    const gridDocId = `${docId}-grid` // Separate namespace for grid

    // Create Y.Doc
    const ydoc = getYDoc(gridDocId, true)
    ydocRef.current = ydoc

    // Get Y.Array for rows
    const yarray = getYArray(ydoc, 'rows')
    yarrayRef.current = yarray

    // Initialize with empty rows if needed
    if (yarray.length === 0) {
      // Add 10 empty rows by default
      for (let i = 0; i < 10; i++) {
        const row = new Y.Map()
        columns.forEach((col) => row.set(col, ''))
        yarray.push([row])
      }
    }

    // Update local rows from Y.Array
    const updateRows = () => {
      const rowsArray = yarray.toArray()
      setRows(rowsArray)
    }

    updateRows()

    // Listen to Y.Array changes
    yarray.observe(updateRows)

    // Create WebSocket provider
    const provider = createWebSocketProvider(gridDocId, ydoc, token, (status) => {
      setConnectionStatus(status)
    })
    providerRef.current = provider

    // Cleanup on unmount
    return () => {
      yarray.unobserve(updateRows)
      destroyWebSocketProvider(gridDocId)
    }
  }, [docId, token])

  // Handle cell click
  const handleCellClick = (row: number, col: number) => {
    setActiveCell({ row, col })
  }

  // Handle cell double-click (start editing)
  const handleCellDoubleClick = (row: number, col: number) => {
    setEditingCell({ row, col })

    // Get current cell value
    const rowData = rows[row]
    const colName = columns[col]
    setCellValue(rowData?.get(colName) || '')
  }

  // Handle cell edit
  const handleCellChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setCellValue(e.target.value)
  }

  // Handle cell blur (finish editing)
  const handleCellBlur = () => {
    if (!editingCell || !yarrayRef.current) return

    const { row, col } = editingCell
    const colName = columns[col]

    // Update Y.Array
    const rowData = yarrayRef.current.get(row)
    if (rowData) {
      rowData.set(colName, cellValue)
    }

    setEditingCell(null)
  }

  // Handle Enter key (finish editing)
  const handleCellKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleCellBlur()
    } else if (e.key === 'Escape') {
      setEditingCell(null)
    }
  }

  // Add row
  const addRow = () => {
    if (!yarrayRef.current) return

    const row = new Y.Map()
    columns.forEach((col) => row.set(col, ''))
    yarrayRef.current.push([row])
  }

  // Delete row
  const deleteRow = (rowIndex: number) => {
    if (!yarrayRef.current) return
    yarrayRef.current.delete(rowIndex, 1)
  }

  // Import CSV
  const importCSV = async () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.csv'

    input.onchange = async (e: any) => {
      const file = e.target.files?.[0]
      if (!file) return

      const text = await file.text()
      const lines = text.split('\n').filter((line) => line.trim())

      if (!yarrayRef.current) return

      // Clear existing rows
      yarrayRef.current.delete(0, yarrayRef.current.length)

      // Parse CSV and add rows
      lines.forEach((line) => {
        const cells = line.split(',')
        const row = new Y.Map()

        cells.forEach((cell, i) => {
          if (i < columns.length) {
            row.set(columns[i], cell.trim())
          }
        })

        yarrayRef.current!.push([row])
      })
    }

    input.click()
  }

  // Export CSV
  const exportCSV = () => {
    if (!rows.length) return

    // Convert rows to CSV
    const csvLines = rows.map((row) => {
      return columns.map((col) => row.get(col) || '').join(',')
    })

    const csv = csvLines.join('\n')

    // Download
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `grid-${docId.substring(0, 8)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  // Export JSON
  const exportJSON = () => {
    if (!rows.length) return

    // Convert rows to array of objects
    const data = rows.map((row) => {
      const obj: Record<string, any> = {}
      columns.forEach((col) => {
        obj[col] = row.get(col) || ''
      })
      return obj
    })

    const json = JSON.stringify(data, null, 2)

    // Download
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `grid-${docId.substring(0, 8)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  // Fetch snapshots
  const fetchSnapshots = async () => {
    setLoadingSnapshots(true)
    try {
      const response = await fetch(`/api/v1/collab/docs/${docId}/snapshots`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      if (response.ok) {
        const data = await response.json()
        // Sort by modified_ts descending
        const sorted = data.sort((a: Snapshot, b: Snapshot) => b.modified_ts - a.modified_ts)
        setSnapshots(sorted.slice(0, 10)) // Show last 10
      } else {
        console.error('Failed to fetch snapshots:', response.statusText)
      }
    } catch (error) {
      console.error('Error fetching snapshots:', error)
    } finally {
      setLoadingSnapshots(false)
    }
  }

  // Restore snapshot
  const restoreSnapshot = async (snapshotId: string) => {
    if (!confirm(`Restore this version? Current changes will be lost.`)) {
      return
    }

    setRestoringSnapshot(true)
    try {
      const response = await fetch(`/api/v1/collab/docs/${docId}/restore`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ snapshot_id: snapshotId })
      })

      if (response.ok) {
        alert('Snapshot restored successfully! Reconnecting...')
        // Reconnect to sync the restored state
        window.location.reload()
      } else {
        const error = await response.json()
        alert(`Restore failed: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Error restoring snapshot:', error)
      alert('Restore failed. Check console for details.')
    } finally {
      setRestoringSnapshot(false)
      setShowHistory(false)
    }
  }

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700">
        {/* Left: Connection Status */}
        <div className="flex items-center gap-2">
          {connectionStatus === 'connected' || connectionStatus === 'synced' ? (
            <Wifi className="w-4 h-4 text-green-600 dark:text-green-400" />
          ) : (
            <WifiOff className="w-4 h-4 text-gray-400" />
          )}
          <span className="text-xs text-gray-600 dark:text-gray-400">
            {connectionStatus === 'synced'
              ? 'Synced'
              : connectionStatus === 'connected'
              ? 'Connected'
              : 'Offline'}
          </span>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={addRow}
            className="flex items-center gap-1 px-3 py-1.5 text-xs rounded bg-primary-600 hover:bg-primary-700 text-white"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Row
          </button>

          <button
            onClick={importCSV}
            className="flex items-center gap-1 px-3 py-1.5 text-xs rounded bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
          >
            <Upload className="w-3.5 h-3.5" />
            Import CSV
          </button>

          <button
            onClick={exportCSV}
            className="flex items-center gap-1 px-3 py-1.5 text-xs rounded bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
          >
            <Download className="w-3.5 h-3.5" />
            CSV
          </button>

          <button
            onClick={exportJSON}
            className="flex items-center gap-1 px-3 py-1.5 text-xs rounded bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
          >
            <Download className="w-3.5 h-3.5" />
            JSON
          </button>

          {/* History Dropdown */}
          <div className="relative">
            <button
              onClick={() => {
                setShowHistory(!showHistory)
                if (!showHistory && snapshots.length === 0) {
                  fetchSnapshots()
                }
              }}
              className="flex items-center gap-1 px-3 py-1.5 text-xs rounded bg-blue-100 dark:bg-blue-900/30 hover:bg-blue-200 dark:hover:bg-blue-900/50 text-blue-700 dark:text-blue-300"
            >
              <History className="w-3.5 h-3.5" />
              History
            </button>

            {/* Dropdown Menu */}
            {showHistory && (
              <div className="absolute right-0 mt-1 w-80 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-10 max-h-96 overflow-y-auto">
                <div className="p-3 border-b border-gray-200 dark:border-gray-700">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                    Version History
                  </h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Last 10 snapshots
                  </p>
                </div>

                {loadingSnapshots ? (
                  <div className="p-8 text-center">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto text-gray-400" />
                    <p className="text-xs text-gray-500 mt-2">Loading...</p>
                  </div>
                ) : snapshots.length === 0 ? (
                  <div className="p-8 text-center">
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      No snapshots available yet
                    </p>
                  </div>
                ) : (
                  <ul className="divide-y divide-gray-200 dark:divide-gray-700">
                    {snapshots.map((snapshot) => (
                      <li
                        key={snapshot.id}
                        className="p-3 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-medium text-gray-900 dark:text-gray-100 truncate">
                              {new Date(snapshot.modified_ts * 1000).toLocaleString()}
                            </p>
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                              {(snapshot.size_bytes / 1024).toFixed(1)} KB
                            </p>
                          </div>
                          <button
                            onClick={() => restoreSnapshot(snapshot.id)}
                            disabled={restoringSnapshot}
                            className="ml-3 flex items-center gap-1 px-2 py-1 text-xs rounded bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white"
                          >
                            <RotateCcw className="w-3 h-3" />
                            Restore
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Grid */}
      <div className="flex-1 overflow-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-gray-100 dark:bg-gray-800">
              <th className="w-12 px-2 py-2 border border-gray-300 dark:border-gray-700 text-xs font-medium text-gray-600 dark:text-gray-400">
                #
              </th>
              {columns.map((col) => (
                <th
                  key={col}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-700 text-xs font-medium text-gray-700 dark:text-gray-300 min-w-[150px]"
                >
                  {col}
                </th>
              ))}
              <th className="w-12 px-2 py-2 border border-gray-300 dark:border-gray-700"></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={rowIndex} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                <td className="px-2 py-2 border border-gray-300 dark:border-gray-700 text-xs text-center text-gray-500">
                  {rowIndex + 1}
                </td>
                {columns.map((col, colIndex) => {
                  const isActive = activeCell?.row === rowIndex && activeCell?.col === colIndex
                  const isEditing = editingCell?.row === rowIndex && editingCell?.col === colIndex

                  return (
                    <td
                      key={col}
                      onClick={() => handleCellClick(rowIndex, colIndex)}
                      onDoubleClick={() => handleCellDoubleClick(rowIndex, colIndex)}
                      className={`px-2 py-2 border border-gray-300 dark:border-gray-700 text-sm ${
                        isActive
                          ? 'ring-2 ring-primary-500 ring-inset'
                          : ''
                      }`}
                    >
                      {isEditing ? (
                        <input
                          type="text"
                          value={cellValue}
                          onChange={handleCellChange}
                          onBlur={handleCellBlur}
                          onKeyDown={handleCellKeyDown}
                          autoFocus
                          className="w-full px-1 py-0.5 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none"
                        />
                      ) : (
                        <div className="px-1 py-0.5 text-gray-900 dark:text-gray-100">
                          {row.get(col) || ''}
                        </div>
                      )}
                    </td>
                  )
                })}
                <td className="px-2 py-2 border border-gray-300 dark:border-gray-700 text-center">
                  <button
                    onClick={() => deleteRow(rowIndex)}
                    className="p-1 rounded hover:bg-red-50 dark:hover:bg-red-900/20 text-red-600 dark:text-red-400"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer Info */}
      {connectionStatus === 'disconnected' && (
        <div className="px-4 py-2 bg-amber-50 dark:bg-amber-900/20 border-t border-amber-200 dark:border-amber-800">
          <p className="text-xs text-amber-800 dark:text-amber-200">
            Offline mode - Your changes are saved locally and will sync when connection is restored.
          </p>
        </div>
      )}
    </div>
  )
}
