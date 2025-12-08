/**
 * Formula Bar Component
 *
 * Excel-style formula bar with autocomplete
 * Translates Excel formulas to DuckDB SQL
 */

import { useState, useRef, useEffect } from 'react'
import { Function, ChevronDown, AlertCircle, CheckCircle } from 'lucide-react'
import toast from 'react-hot-toast'

interface FormulaBarProps {
  value: string
  onValueChange: (value: string) => void
  onFormulaApply?: (formula: string, sql?: string) => void
  cellReference?: string
  disabled?: boolean
}

const EXCEL_FORMULAS = [
  { name: 'SUM', syntax: '=SUM(A1:A10)', description: 'Add up a range of numbers' },
  { name: 'AVERAGE', syntax: '=AVERAGE(A1:A10)', description: 'Calculate average of numbers' },
  { name: 'COUNT', syntax: '=COUNT(A1:A10)', description: 'Count cells with numbers' },
  { name: 'COUNTIF', syntax: '=COUNTIF(A1:A10, ">5")', description: 'Count cells matching criteria' },
  { name: 'IF', syntax: '=IF(A1>10, "High", "Low")', description: 'Conditional logic' },
  { name: 'VLOOKUP', syntax: '=VLOOKUP(value, A1:B10, 2, FALSE)', description: 'Vertical lookup in table' },
  { name: 'SUMIF', syntax: '=SUMIF(A1:A10, ">5")', description: 'Sum cells matching criteria' },
  { name: 'MAX', syntax: '=MAX(A1:A10)', description: 'Find maximum value' },
  { name: 'MIN', syntax: '=MIN(A1:A10)', description: 'Find minimum value' },
  { name: 'CONCAT', syntax: '=CONCAT(A1, " ", B1)', description: 'Concatenate text' },
]

export function FormulaBar({
  value,
  onValueChange,
  onFormulaApply,
  cellReference = 'A1',
  disabled = false,
}: FormulaBarProps) {
  const [formula, setFormula] = useState(value)
  const [suggestions, setSuggestions] = useState<typeof EXCEL_FORMULAS>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(0)
  const [translating, setTranslating] = useState(false)
  const [translationStatus, setTranslationStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    setFormula(value)
  }, [value])

  function handleFormulaInput(newValue: string) {
    setFormula(newValue)
    onValueChange(newValue)

    // Show autocomplete suggestions for Excel formulas
    if (newValue.startsWith('=')) {
      const query = newValue.slice(1).toUpperCase()
      const filtered = EXCEL_FORMULAS.filter(
        (f) =>
          f.name.includes(query) ||
          f.syntax.toUpperCase().includes(query) ||
          f.description.toUpperCase().includes(query)
      )

      setSuggestions(filtered)
      setShowSuggestions(filtered.length > 0)
      setSelectedSuggestionIndex(0)
    } else {
      setShowSuggestions(false)
    }
  }

  async function translateFormula(excelFormula: string): Promise<string | null> {
    setTranslating(true)
    setTranslationStatus('idle')

    try {
      // TODO: Replace with actual API call when backend is ready
      // const response = await fetch('/api/v1/sheets/translate-formula', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ formula: excelFormula })
      // })
      // const data = await response.json()
      // return data.sql

      // Mock translation for now
      await new Promise((resolve) => setTimeout(resolve, 500))

      // Simple mock translations
      if (excelFormula.toUpperCase().includes('SUM')) {
        setTranslationStatus('success')
        return 'SELECT SUM(column) FROM sheet WHERE rownum BETWEEN start AND end'
      } else if (excelFormula.toUpperCase().includes('AVERAGE')) {
        setTranslationStatus('success')
        return 'SELECT AVG(column) FROM sheet WHERE rownum BETWEEN start AND end'
      } else if (excelFormula.toUpperCase().includes('COUNT')) {
        setTranslationStatus('success')
        return 'SELECT COUNT(column) FROM sheet WHERE condition'
      } else {
        throw new Error('Formula not yet supported')
      }
    } catch (err) {
      setTranslationStatus('error')
      toast.error(`Unsupported formula: ${err instanceof Error ? err.message : 'Unknown error'}`)
      return null
    } finally {
      setTranslating(false)
    }
  }

  async function handleApplyFormula() {
    if (!formula.trim()) {
      return
    }

    if (formula.startsWith('=')) {
      // Excel formula - translate to SQL
      const sql = await translateFormula(formula)
      if (sql) {
        onFormulaApply?.(formula, sql)
        toast.success('Formula translated successfully')
      }
    } else {
      // Plain value
      onFormulaApply?.(formula)
    }

    setShowSuggestions(false)
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (showSuggestions && suggestions.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedSuggestionIndex((i) => (i + 1) % suggestions.length)
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedSuggestionIndex((i) => (i - 1 + suggestions.length) % suggestions.length)
      } else if (e.key === 'Tab' || (e.key === 'Enter' && showSuggestions)) {
        e.preventDefault()
        selectSuggestion(suggestions[selectedSuggestionIndex])
      } else if (e.key === 'Escape') {
        setShowSuggestions(false)
      }
    } else if (e.key === 'Enter') {
      e.preventDefault()
      handleApplyFormula()
    }
  }

  function selectSuggestion(suggestion: typeof EXCEL_FORMULAS[0]) {
    setFormula(suggestion.syntax)
    onValueChange(suggestion.syntax)
    setShowSuggestions(false)

    // Move cursor to end
    setTimeout(() => {
      inputRef.current?.focus()
      inputRef.current?.setSelectionRange(suggestion.syntax.length, suggestion.syntax.length)
    }, 0)
  }

  return (
    <div className="relative">
      <div className="flex items-center gap-2 p-2 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        {/* Cell Reference */}
        <div className="flex items-center gap-1 px-3 py-1.5 bg-gray-100 dark:bg-gray-700 rounded text-sm font-mono text-gray-700 dark:text-gray-300">
          <span className="font-semibold">{cellReference}</span>
        </div>

        {/* Formula Icon */}
        <div className="p-1.5 text-gray-600 dark:text-gray-400">
          <Function className="w-4 h-4" />
        </div>

        {/* Formula Input */}
        <div className="flex-1 relative">
          <input
            ref={inputRef}
            type="text"
            value={formula}
            onChange={(e) => handleFormulaInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => {
              if (formula.startsWith('=')) {
                handleFormulaInput(formula)
              }
            }}
            disabled={disabled}
            placeholder="Enter value or =SUM(A1:A10)"
            className="w-full px-3 py-1.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          />

          {/* Translation Status Indicator */}
          {translating && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
            </div>
          )}

          {!translating && translationStatus === 'success' && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              <CheckCircle className="w-4 h-4 text-green-500" />
            </div>
          )}

          {!translating && translationStatus === 'error' && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              <AlertCircle className="w-4 h-4 text-red-500" />
            </div>
          )}
        </div>

        {/* Apply Button */}
        <button
          onClick={handleApplyFormula}
          disabled={disabled || translating || !formula.trim()}
          className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Apply
        </button>
      </div>

      {/* Autocomplete Suggestions */}
      {showSuggestions && suggestions.length > 0 && (
        <div className="absolute left-0 right-0 top-full mt-1 z-50 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl max-h-80 overflow-y-auto">
          <div className="p-2">
            <div className="px-3 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Excel Functions
            </div>
            {suggestions.map((suggestion, index) => {
              const isSelected = index === selectedSuggestionIndex

              return (
                <button
                  key={suggestion.name}
                  onClick={() => selectSuggestion(suggestion)}
                  onMouseEnter={() => setSelectedSuggestionIndex(index)}
                  className={`w-full flex items-start gap-3 px-3 py-2.5 rounded-lg text-left transition-colors ${
                    isSelected
                      ? 'bg-blue-50 dark:bg-blue-900/30'
                      : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
                  }`}
                >
                  <div
                    className={`p-1.5 rounded ${
                      isSelected
                        ? 'bg-blue-100 dark:bg-blue-900/50'
                        : 'bg-gray-100 dark:bg-gray-700'
                    }`}
                  >
                    <Function
                      className={`w-3 h-3 ${
                        isSelected
                          ? 'text-blue-600 dark:text-blue-400'
                          : 'text-gray-600 dark:text-gray-400'
                      }`}
                    />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div
                      className={`text-sm font-medium font-mono ${
                        isSelected
                          ? 'text-blue-900 dark:text-blue-100'
                          : 'text-gray-900 dark:text-gray-100'
                      }`}
                    >
                      {suggestion.syntax}
                    </div>
                    <div className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
                      {suggestion.description}
                    </div>
                  </div>
                </button>
              )
            })}
          </div>

          {/* Footer hint */}
          <div className="px-4 py-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
            <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
              <span>↑↓ Navigate</span>
              <span>Tab/↵ Select</span>
              <span>Esc Close</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
