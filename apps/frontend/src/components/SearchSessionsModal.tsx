/**
 * Search Sessions Modal - Sprint 6 Theme B (Ticket B3)
 *
 * Full-text search over session messages with filters
 */

import { useState, useEffect, useRef } from 'react'
import { Search, X, Clock, Calendar, MessageSquare, Sparkles, Filter } from 'lucide-react'
import {
  searchSessions,
  saveRecentSearch,
  getRecentSearches,
  type SearchResult,
  type SearchFilters
} from '../lib/searchApi'
import { showToast } from '../lib/toast'
import { useChatStore } from '../stores/chatStore'

interface SearchSessionsModalProps {
  onClose: () => void
}

export function SearchSessionsModal({ onClose }: SearchSessionsModalProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState<SearchFilters>({})
  const [recentSearches, setRecentSearches] = useState<string[]>([])
  const inputRef = useRef<HTMLInputElement>(null)
  const { setActiveChatId } = useChatStore()

  useEffect(() => {
    inputRef.current?.focus()
    setRecentSearches(getRecentSearches())
  }, [])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  // Debounced search
  useEffect(() => {
    if (!query || query.length < 2) {
      setResults([])
      return
    }

    const timer = setTimeout(() => {
      performSearch(query)
    }, 300)

    return () => clearTimeout(timer)
  }, [query, filters])

  const performSearch = async (searchQuery: string) => {
    setLoading(true)

    try {
      const response = await searchSessions(searchQuery, filters)
      setResults(response.results)

      if (searchQuery.length >= 3) {
        saveRecentSearch(searchQuery)
        setRecentSearches(getRecentSearches())
      }
    } catch (error: any) {
      showToast.error(error.message || 'Search failed')
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const handleResultClick = (sessionId: string) => {
    setActiveChatId(sessionId)
    onClose()
  }

  const handleRecentClick = (recentQuery: string) => {
    setQuery(recentQuery)
  }

  return (
    <div
      className="fixed inset-0 bg-black/50 dark:bg-black/70 flex items-start justify-center z-50 p-4 pt-20"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-3xl max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Header */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <Search className="w-5 h-5 text-gray-400 flex-shrink-0" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search sessions..."
              className="flex-1 bg-transparent border-none outline-none text-gray-900 dark:text-gray-100 placeholder-gray-400"
            />
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`p-2 rounded-lg transition-colors ${
                showFilters
                  ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                  : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500'
              }`}
              title="Filters"
            >
              <Filter size={18} />
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              <X size={18} />
            </button>
          </div>

          {/* Filters */}
          {showFilters && (
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 grid grid-cols-2 gap-3">
              <input
                type="text"
                placeholder="Model name..."
                value={filters.model || ''}
                onChange={(e) => setFilters({ ...filters, model: e.target.value || undefined })}
                className="px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-sm"
              />
              <input
                type="date"
                placeholder="From date..."
                value={filters.fromDate?.split('T')[0] || ''}
                onChange={(e) => setFilters({ ...filters, fromDate: e.target.value ? new Date(e.target.value).toISOString() : undefined })}
                className="px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-sm"
              />
            </div>
          )}
        </div>

        {/* Results */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading && (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          )}

          {!loading && query.length === 0 && (
            <div className="space-y-4">
              {recentSearches.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mb-2 flex items-center gap-2">
                    <Clock size={14} />
                    Recent Searches
                  </h3>
                  <div className="space-y-1">
                    {recentSearches.map((recent, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleRecentClick(recent)}
                        className="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                      >
                        {recent}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div className="text-center py-12">
                <Search className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
                <p className="text-gray-500 dark:text-gray-400 text-sm">
                  Search your sessions by message content
                </p>
              </div>
            </div>
          )}

          {!loading && query.length > 0 && results.length === 0 && (
            <div className="text-center py-12">
              <Search className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500 dark:text-gray-400">No results found for "{query}"</p>
            </div>
          )}

          {!loading && results.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                {results.length} {results.length === 1 ? 'result' : 'results'} found
              </p>
              {results.map((result) => (
                <button
                  key={result.session_id}
                  onClick={() => handleResultClick(result.session_id)}
                  className="w-full text-left p-4 bg-gray-50 dark:bg-gray-900 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors border border-gray-200 dark:border-gray-700"
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <MessageSquare size={16} className="text-gray-400 flex-shrink-0" />
                      <h4 className="font-medium text-gray-900 dark:text-gray-100 truncate">
                        {result.title}
                      </h4>
                    </div>
                    <span className="text-xs text-gray-500 dark:text-gray-400 flex-shrink-0">
                      {result.match_count} {result.match_count === 1 ? 'match' : 'matches'}
                    </span>
                  </div>

                  <div
                    className="text-sm text-gray-600 dark:text-gray-400 mb-2 line-clamp-2"
                    dangerouslySetInnerHTML={{ __html: result.snippet.replace(/<mark>/g, '<mark class="bg-yellow-200 dark:bg-yellow-900 px-1 rounded">') }}
                  />

                  <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                    {result.model_name && (
                      <span className="flex items-center gap-1">
                        <Sparkles size={12} />
                        {result.model_name}
                      </span>
                    )}
                    <span className="flex items-center gap-1">
                      <Calendar size={12} />
                      {new Date(result.ts).toLocaleDateString()}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded text-xs">
                Esc
              </kbd>
              Close
            </span>
          </div>
          <div>
            Powered by FTS5
          </div>
        </div>
      </div>
    </div>
  )
}
