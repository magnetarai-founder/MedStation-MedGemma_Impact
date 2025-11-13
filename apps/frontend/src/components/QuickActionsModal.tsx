import { useEffect, useState, useRef } from 'react'
import { Search, Command } from 'lucide-react'
import { QuickAction, ActionsContext, getActions, searchActions, getCategoryLabel } from '../lib/actionsRegistry'

interface QuickActionsModalProps {
  context: ActionsContext
  onClose: () => void
}

export function QuickActionsModal({ context, onClose }: QuickActionsModalProps) {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  // Get all available actions based on context
  const allActions = getActions(context)

  // Filter actions based on search query
  const filteredActions = searchActions(allActions, query)

  // Reset selection when filtered results change
  useEffect(() => {
    setSelectedIndex(0)
  }, [query])

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'Escape':
          e.preventDefault()
          onClose()
          break

        case 'ArrowDown':
          e.preventDefault()
          setSelectedIndex(prev => Math.min(prev + 1, filteredActions.length - 1))
          break

        case 'ArrowUp':
          e.preventDefault()
          setSelectedIndex(prev => Math.max(prev - 1, 0))
          break

        case 'Enter':
          e.preventDefault()
          if (filteredActions[selectedIndex]) {
            executeAction(filteredActions[selectedIndex])
          }
          break

        default:
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [filteredActions, selectedIndex, onClose])

  // Scroll selected item into view
  useEffect(() => {
    const selectedElement = listRef.current?.children[selectedIndex] as HTMLElement
    if (selectedElement) {
      selectedElement.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    }
  }, [selectedIndex])

  const executeAction = async (action: QuickAction) => {
    try {
      await action.run()
      onClose() // Close modal on success
    } catch (error) {
      console.error('Failed to execute action:', error)
      // Don't close on error - let user retry
    }
  }

  // Group actions by category
  const actionsByCategory = filteredActions.reduce((acc, action) => {
    if (!acc[action.category]) {
      acc[action.category] = []
    }
    acc[action.category].push(action)
    return acc
  }, {} as Record<string, QuickAction[]>)

  const categories = Object.keys(actionsByCategory) as Array<QuickAction['category']>

  // Calculate flat index for keyboard navigation across categories
  let flatIndex = 0

  return (
    <div
      className="fixed inset-0 bg-black/50 dark:bg-black/70 flex items-start justify-center z-50 p-4 pt-20"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="quick-actions-title"
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header with Search */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" aria-hidden="true" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search actions..."
              className="w-full pl-10 pr-4 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900 dark:text-gray-100"
              aria-label="Search actions"
              id="quick-actions-search"
            />
          </div>
        </div>

        {/* Results */}
        <div
          ref={listRef}
          className="max-h-96 overflow-y-auto"
          role="listbox"
          aria-labelledby="quick-actions-title"
        >
          {filteredActions.length === 0 ? (
            <div className="p-8 text-center text-gray-500 dark:text-gray-400">
              <p className="text-sm">No actions found</p>
              <p className="text-xs mt-1">Try a different search term</p>
            </div>
          ) : (
            categories.map((category) => (
              <div key={category} className="py-2">
                {/* Category Header */}
                <div className="px-4 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  {getCategoryLabel(category)}
                </div>

                {/* Actions in Category */}
                {actionsByCategory[category].map((action) => {
                  const isSelected = filteredActions[selectedIndex]?.id === action.id
                  const currentFlatIndex = flatIndex++

                  return (
                    <button
                      key={action.id}
                      onClick={() => executeAction(action)}
                      className={`w-full px-4 py-3 flex items-center gap-3 text-left transition-colors ${
                        isSelected
                          ? 'bg-blue-50 dark:bg-blue-900/20 border-l-2 border-blue-600'
                          : 'hover:bg-gray-50 dark:hover:bg-gray-900/50'
                      }`}
                      role="option"
                      aria-selected={isSelected}
                      tabIndex={-1}
                    >
                      {/* Icon */}
                      {action.icon && (
                        <span className="text-2xl" aria-hidden="true">
                          {action.icon}
                        </span>
                      )}

                      {/* Label and Keywords */}
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {action.label}
                        </div>
                        {action.keywords.length > 0 && (
                          <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                            {action.keywords.slice(0, 3).join(', ')}
                          </div>
                        )}
                      </div>

                      {/* Selection Indicator */}
                      {isSelected && (
                        <div className="flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400">
                          <Command size={12} aria-hidden="true" />
                          <span>Enter</span>
                        </div>
                      )}
                    </button>
                  )
                })}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded text-xs">
                ↑↓
              </kbd>
              Navigate
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded text-xs">
                Enter
              </kbd>
              Select
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded text-xs">
                Esc
              </kbd>
              Close
            </span>
          </div>
          <div className="text-gray-400 dark:text-gray-500">
            {filteredActions.length} {filteredActions.length === 1 ? 'action' : 'actions'}
          </div>
        </div>
      </div>
    </div>
  )
}
