/**
 * Spreadsheet Editor
 *
 * Lightweight collaborative spreadsheet for church needs:
 * - Donation tracking, volunteer schedules, rosters, budgets, attendance
 * - Grid editing with formulas
 * - Excel/CSV import
 * - Simple and intuitive for non-technical users
 */

import { useState, useRef, useEffect } from 'react'
import { Upload, Download, Plus, Trash2, Bold, DollarSign, Percent, Hash } from 'lucide-react'
import toast from 'react-hot-toast'

interface Cell {
  value: string
  formula?: string
  format?: 'text' | 'number' | 'currency' | 'percent'
  bold?: boolean
}

interface SpreadsheetData {
  rows: Cell[][]
  columns: string[] // Column headers (A, B, C, etc.)
}

interface SpreadsheetEditorProps {
  data: SpreadsheetData
  onChange: (data: SpreadsheetData) => void
  onSave: () => void
}

export function SpreadsheetEditor({ data, onChange, onSave }: SpreadsheetEditorProps) {
  const [selectedCell, setSelectedCell] = useState<{ row: number; col: number } | null>(null)
  const [editingCell, setEditingCell] = useState<{ row: number; col: number } | null>(null)
  const [editValue, setEditValue] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Initialize with default grid if empty
  useEffect(() => {
    if (!data.rows || !data.columns || data.rows.length === 0) {
      const defaultData: SpreadsheetData = {
        columns: generateColumnHeaders(10),
        rows: Array(20).fill(null).map(() =>
          Array(10).fill(null).map(() => ({ value: '', format: 'text' }))
        )
      }
      onChange(defaultData)
    }
  }, [])

  // Focus input when editing starts
  useEffect(() => {
    if (editingCell && inputRef.current) {
      inputRef.current.focus()
    }
  }, [editingCell])

  // Generate column headers (A, B, C, ..., Z, AA, AB, ...)
  function generateColumnHeaders(count: number): string[] {
    const headers: string[] = []
    for (let i = 0; i < count; i++) {
      let header = ''
      let num = i
      while (num >= 0) {
        header = String.fromCharCode(65 + (num % 26)) + header
        num = Math.floor(num / 26) - 1
      }
      headers.push(header)
    }
    return headers
  }

  // Handle cell click
  const handleCellClick = (row: number, col: number) => {
    setSelectedCell({ row, col })
    setEditingCell(null)
  }

  // Handle cell double-click to edit
  const handleCellDoubleClick = (row: number, col: number) => {
    const cell = data.rows[row]?.[col]
    if (!cell) return

    setEditingCell({ row, col })
    setSelectedCell({ row, col })
    setEditValue(cell.formula || cell.value)
  }

  // Handle cell value change
  const handleCellChange = (row: number, col: number, value: string) => {
    const newRows = [...data.rows]
    if (!newRows[row]) return

    const cell = { ...newRows[row][col] }

    // Check if it's a formula
    if (value.startsWith('=')) {
      cell.formula = value
      cell.value = evaluateFormula(value, newRows)
    } else {
      cell.value = value
      cell.formula = undefined
    }

    newRows[row][col] = cell
    onChange({ ...data, rows: newRows })
  }

  // Simple formula evaluator (SUM, AVERAGE, COUNT)
  const evaluateFormula = (formula: string, rows: Cell[][]): string => {
    try {
      formula = formula.substring(1) // Remove '='

      // SUM(A1:A5)
      if (formula.toUpperCase().startsWith('SUM(')) {
        const range = formula.match(/SUM\(([A-Z]+\d+):([A-Z]+\d+)\)/i)
        if (range) {
          const values = getRangeValues(range[1], range[2], rows)
          const sum = values.reduce((acc, val) => acc + parseFloat(val || '0'), 0)
          return sum.toString()
        }
      }

      // AVERAGE(A1:A5)
      if (formula.toUpperCase().startsWith('AVERAGE(')) {
        const range = formula.match(/AVERAGE\(([A-Z]+\d+):([A-Z]+\d+)\)/i)
        if (range) {
          const values = getRangeValues(range[1], range[2], rows)
          const nums = values.map(v => parseFloat(v || '0'))
          const avg = nums.reduce((a, b) => a + b, 0) / nums.length
          return avg.toFixed(2)
        }
      }

      // COUNT(A1:A5)
      if (formula.toUpperCase().startsWith('COUNT(')) {
        const range = formula.match(/COUNT\(([A-Z]+\d+):([A-Z]+\d+)\)/i)
        if (range) {
          const values = getRangeValues(range[1], range[2], rows)
          return values.filter(v => v && v.trim() !== '').length.toString()
        }
      }

      return '#ERROR'
    } catch (e) {
      return '#ERROR'
    }
  }

  // Get values from a cell range (e.g., A1:A5)
  const getRangeValues = (start: string, end: string, rows: Cell[][]): string[] => {
    const startPos = cellRefToPosition(start)
    const endPos = cellRefToPosition(end)

    const values: string[] = []
    for (let row = startPos.row; row <= endPos.row; row++) {
      for (let col = startPos.col; col <= endPos.col; col++) {
        values.push(rows[row]?.[col]?.value || '')
      }
    }
    return values
  }

  // Convert cell reference (e.g., "A1") to position
  const cellRefToPosition = (ref: string): { row: number; col: number } => {
    const match = ref.match(/([A-Z]+)(\d+)/)
    if (!match) return { row: 0, col: 0 }

    const colStr = match[1]
    const rowNum = parseInt(match[2]) - 1

    let col = 0
    for (let i = 0; i < colStr.length; i++) {
      col = col * 26 + (colStr.charCodeAt(i) - 64)
    }
    col -= 1

    return { row: rowNum, col }
  }

  // Handle finish editing
  const handleFinishEdit = () => {
    if (editingCell) {
      handleCellChange(editingCell.row, editingCell.col, editValue)
      setEditingCell(null)
    }
  }

  // Handle key press in edit mode
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleFinishEdit()
    } else if (e.key === 'Escape') {
      setEditingCell(null)
      setEditValue('')
    }
  }

  // Add row
  const addRow = () => {
    const newRows = [
      ...data.rows,
      Array(data.columns.length).fill(null).map(() => ({ value: '', format: 'text' as const }))
    ]
    onChange({ ...data, rows: newRows })
  }

  // Add column
  const addColumn = () => {
    const newColumns = [...data.columns, generateColumnHeaders(data.columns.length + 1)[data.columns.length]]
    const newRows = data.rows.map(row => [...row, { value: '', format: 'text' as const }])
    onChange({ columns: newColumns, rows: newRows })
  }

  // Delete row
  const deleteRow = (rowIndex: number) => {
    if (data.rows.length <= 1) {
      toast.error('Must have at least one row')
      return
    }
    const newRows = data.rows.filter((_, i) => i !== rowIndex)
    onChange({ ...data, rows: newRows })
    setSelectedCell(null)
  }

  // Delete column
  const deleteColumn = (colIndex: number) => {
    if (data.columns.length <= 1) {
      toast.error('Must have at least one column')
      return
    }
    const newColumns = data.columns.filter((_, i) => i !== colIndex)
    const newRows = data.rows.map(row => row.filter((_, i) => i !== colIndex))
    onChange({ columns: newColumns, rows: newRows })
    setSelectedCell(null)
  }

  // Toggle cell format
  const toggleFormat = (format: Cell['format']) => {
    if (!selectedCell) return
    const { row, col } = selectedCell
    const newRows = [...data.rows]
    const cell = { ...newRows[row][col] }
    cell.format = cell.format === format ? 'text' : format
    newRows[row][col] = cell
    onChange({ ...data, rows: newRows })
  }

  // Toggle bold
  const toggleBold = () => {
    if (!selectedCell) return
    const { row, col } = selectedCell
    const newRows = [...data.rows]
    const cell = { ...newRows[row][col] }
    cell.bold = !cell.bold
    newRows[row][col] = cell
    onChange({ ...data, rows: newRows })
  }

  // Format cell value for display
  const formatCellValue = (cell: Cell): string => {
    if (!cell.value) return ''

    switch (cell.format) {
      case 'currency':
        const num = parseFloat(cell.value)
        return isNaN(num) ? cell.value : `$${num.toFixed(2)}`
      case 'percent':
        const pct = parseFloat(cell.value)
        return isNaN(pct) ? cell.value : `${pct}%`
      case 'number':
        const n = parseFloat(cell.value)
        return isNaN(n) ? cell.value : n.toString()
      default:
        return cell.value
    }
  }

  // Export to CSV
  const exportToCSV = () => {
    const csv = data.rows.map(row =>
      row.map(cell => `"${cell.value}"`).join(',')
    ).join('\n')

    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'spreadsheet.csv'
    a.click()
    URL.revokeObjectURL(url)
    toast.success('Exported to CSV')
  }

  // Import from CSV/Excel
  const handleFileImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (event) => {
      const text = event.target?.result as string
      const lines = text.split('\n')
      const newRows = lines.map(line => {
        const values = line.split(',').map(v => v.trim().replace(/^"|"$/g, ''))
        return values.map(value => ({ value, format: 'text' as const }))
      })

      const maxCols = Math.max(...newRows.map(row => row.length))
      const newColumns = generateColumnHeaders(maxCols)

      onChange({ columns: newColumns, rows: newRows })
      toast.success('File imported successfully')
    }
    reader.readAsText(file)

    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-900">
      {/* Main Toolbar - Import/Export/Row/Column */}
      <div className="flex items-center gap-1 p-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
        {/* Import/Export */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={handleFileImport}
          className="hidden"
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          className="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
          title="Import CSV/Excel"
        >
          <Upload className="w-4 h-4" />
        </button>

        <button
          onClick={exportToCSV}
          className="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
          title="Export to CSV"
        >
          <Download className="w-4 h-4" />
        </button>

        {/* Vertical Spacer */}
        <div className="w-px h-5 bg-gray-300 dark:bg-gray-600 mx-1"></div>

        {/* Row/Column */}
        <button
          onClick={addRow}
          className="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
          title="Add Row"
        >
          <Plus className="w-4 h-4" />
        </button>

        <button
          onClick={addColumn}
          className="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
          title="Add Column"
        >
          <Plus className="w-4 h-4" />
        </button>

        {/* Delete buttons (when cell selected) */}
        {selectedCell && (
          <>
            <div className="w-px h-5 bg-gray-300 dark:bg-gray-600 mx-1"></div>
            <button
              onClick={() => deleteRow(selectedCell.row)}
              className="p-2 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600 dark:text-red-400 transition-colors"
              title="Delete Row"
            >
              <Trash2 className="w-4 h-4" />
            </button>

            <button
              onClick={() => deleteColumn(selectedCell.col)}
              className="p-2 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600 dark:text-red-400 transition-colors"
              title="Delete Column"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </>
        )}
      </div>

      {/* Formatting Toolbar - Bold/Number/Currency/Percent */}
      <div className="flex items-center gap-1 p-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
        <button
          onClick={toggleBold}
          disabled={!selectedCell}
          className={`p-2 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
            selectedCell && data.rows[selectedCell.row]?.[selectedCell.col]?.bold
              ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
              : 'hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
          }`}
          title="Bold"
        >
          <Bold className="w-4 h-4" />
        </button>

        <div className="w-px h-5 bg-gray-300 dark:bg-gray-600 mx-1"></div>

        <button
          onClick={() => toggleFormat('number')}
          disabled={!selectedCell}
          className={`p-2 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
            selectedCell && data.rows[selectedCell.row]?.[selectedCell.col]?.format === 'number'
              ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
              : 'hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
          }`}
          title="Number Format"
        >
          <Hash className="w-4 h-4" />
        </button>

        <button
          onClick={() => toggleFormat('currency')}
          disabled={!selectedCell}
          className={`p-2 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
            selectedCell && data.rows[selectedCell.row]?.[selectedCell.col]?.format === 'currency'
              ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
              : 'hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
          }`}
          title="Currency Format"
        >
          <DollarSign className="w-4 h-4" />
        </button>

        <button
          onClick={() => toggleFormat('percent')}
          disabled={!selectedCell}
          className={`p-2 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
            selectedCell && data.rows[selectedCell.row]?.[selectedCell.col]?.format === 'percent'
              ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
              : 'hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
          }`}
          title="Percent Format"
        >
          <Percent className="w-4 h-4" />
        </button>
      </div>

      {/* Formula bar */}
      {selectedCell && (
        <div className="flex items-center gap-2 px-4 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
          <div className="text-xs font-medium text-gray-600 dark:text-gray-400 w-12">
            {data.columns[selectedCell.col]}{selectedCell.row + 1}
          </div>
          <input
            type="text"
            value={editingCell ? editValue : (data.rows[selectedCell.row]?.[selectedCell.col]?.formula || data.rows[selectedCell.row]?.[selectedCell.col]?.value || '')}
            onChange={(e) => setEditValue(e.target.value)}
            onFocus={() => {
              if (!editingCell) {
                setEditingCell(selectedCell)
                setEditValue(data.rows[selectedCell.row]?.[selectedCell.col]?.formula || data.rows[selectedCell.row]?.[selectedCell.col]?.value || '')
              }
            }}
            onBlur={handleFinishEdit}
            onKeyDown={handleKeyDown}
            className="flex-1 px-2 py-1 text-xs bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded focus:outline-none focus:ring-1 focus:ring-primary-500"
            placeholder="Enter value or formula (e.g., =SUM(A1:A5))"
          />
        </div>
      )}

      {/* Grid */}
      <div className="flex-1 overflow-auto relative">
        <table className="border-collapse w-full table-fixed">
          <colgroup>
            <col style={{ width: '48px' }} />
            {data.columns?.map((_, i) => (
              <col key={i} style={{ width: `${100 / data.columns.length}%` }} />
            ))}
          </colgroup>
          <thead className="sticky top-0 z-10">
            <tr>
              <th className="w-12 h-8 border border-gray-300 dark:border-gray-700 bg-gray-100 dark:bg-gray-800 text-xs font-semibold text-gray-600 dark:text-gray-400 sticky left-0 z-20"></th>
              {data.columns?.map((col, i) => (
                <th
                  key={i}
                  className="h-8 border border-gray-300 dark:border-gray-700 bg-gray-100 dark:bg-gray-800 text-xs font-semibold text-gray-600 dark:text-gray-400"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows?.map((row, rowIndex) => (
              <tr key={rowIndex}>
                <td className="w-12 h-9 border border-gray-300 dark:border-gray-700 bg-gray-100 dark:bg-gray-800 text-center text-xs font-semibold text-gray-600 dark:text-gray-400 sticky left-0 z-10">
                  {rowIndex + 1}
                </td>
                {row.map((cell, colIndex) => {
                  const isSelected = selectedCell?.row === rowIndex && selectedCell?.col === colIndex
                  const isEditing = editingCell?.row === rowIndex && editingCell?.col === colIndex

                  return (
                    <td
                      key={colIndex}
                      onClick={() => handleCellClick(rowIndex, colIndex)}
                      onDoubleClick={() => handleCellDoubleClick(rowIndex, colIndex)}
                      className={`h-9 border border-gray-300 dark:border-gray-700 px-2 py-1 text-sm cursor-pointer transition-colors ${
                        isSelected
                          ? 'bg-primary-50 dark:bg-primary-900/20 ring-2 ring-primary-500 ring-inset'
                          : 'bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800'
                      } ${cell.bold ? 'font-semibold' : ''}`}
                    >
                      {isEditing ? (
                        <input
                          ref={inputRef}
                          type="text"
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          onBlur={handleFinishEdit}
                          onKeyDown={handleKeyDown}
                          className="w-full h-full bg-transparent outline-none"
                        />
                      ) : (
                        <div className="truncate">
                          {formatCellValue(cell)}
                        </div>
                      )}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Help text */}
      <div className="px-4 py-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
        <p className="text-xs text-gray-500 dark:text-gray-400">
          <span className="font-medium">Tip:</span> Double-click to edit • Use formulas: =SUM(A1:A5), =AVERAGE(A1:A5), =COUNT(A1:A5)
        </p>
      </div>
    </div>
  )
}
