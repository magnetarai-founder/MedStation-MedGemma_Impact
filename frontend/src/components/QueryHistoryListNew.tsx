import { useState, useCallback, useEffect, useRef } from 'react'
import { Clock, FileText, Trash2, Save, Filter, Loader2 } from 'lucide-react'
import { useInfiniteQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { useNavigationStore } from '@/stores/navigationStore'
import { useSessionStore } from '@/stores/sessionStore'
import { useQueriesStore } from '@/stores/queriesStore'
import * as historyApi from '@/lib/historyApi'
import type { HistoryItem } from '@/lib/historyApi'

const ITEMS_PER_PAGE = 50

export function QueryHistoryListNew() {
  const queryClient = useQueryClient()
  const { setActiveTab } = useNavigationStore()
  const { currentFile } = useSessionStore()
  const { addQuery } = useQueriesStore()
  const [filterType, setFilterType] = useState<'all' | 'sql' | 'json'>('all')
  const [filterDate, setFilterDate] = useState<'all' | 'today' | 'week'>('all')
  const scrollContainerRef = useRef<HTMLDivElement>(null)

  // Infinite scroll query
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    error,
  } = useInfiniteQuery({
    queryKey: ['history', filterType, filterDate],
    queryFn: ({ pageParam = 0 }) =>
      historyApi.getHistory({
        query_type: filterType === 'all' ? undefined : filterType,
        limit: ITEMS_PER_PAGE,
        offset: pageParam,
        date_filter: filterDate,
      }),
    getNextPageParam: (lastPage, allPages) => {
      const loadedItems = allPages.reduce((sum, page) => sum + page.items.length, 0)
      return loadedItems < lastPage.total ? loadedItems : undefined
    },
    staleTime: Infinity, // Cache forever until manual invalidation
    gcTime: 1000 * 60 * 30, // Keep in cache for 30 minutes
    refetchOnMount: false,
    refetchOnWindowFocus: false,
  })

  // Infinite scroll handler
  const handleScroll = useCallback(() => {
    const container = scrollContainerRef.current
    if (!container || isFetchingNextPage || !hasNextPage) return

    const { scrollTop, scrollHeight, clientHeight } = container
    const scrollPercentage = (scrollTop + clientHeight) / scrollHeight

    if (scrollPercentage > 0.8) {
      fetchNextPage()
    }
  }, [fetchNextPage, hasNextPage, isFetchingNextPage])

  useEffect(() => {
    const container = scrollContainerRef.current
    if (!container) return

    container.addEventListener('scroll', handleScroll)
    return () => container.removeEventListener('scroll', handleScroll)
  }, [handleScroll])

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) => historyApi.deleteHistoryItem(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['history'] })
    },
  })

  // Clear history mutation
  const clearMutation = useMutation({
    mutationFn: () => historyApi.clearHistory(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['history'] })
    },
  })

  const formatTimestamp = (timestamp: string) => {
    const now = Date.now()
    const diff = now - new Date(timestamp).getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)

    if (minutes < 1) return 'Just now'
    if (minutes < 60) return `${minutes}m ago`
    if (hours < 24) return `${hours}h ago`
    return `${days}d ago`
  }

  const handleHistoryClick = (item: HistoryItem) => {
    // Check if Excel file is loaded for SQL queries
    if (item.query_type === 'sql' && !currentFile) {
      alert('Please load an Excel or CSV file first')
      return
    }

    // Load query into editor
    window.dispatchEvent(
      new CustomEvent('code-file-loaded', {
        detail: { content: item.query, type: item.query_type },
      })
    )

    // Switch to editor tab
    setActiveTab('editor')
  }

  const handleSaveToQueries = (item: HistoryItem) => {
    const name = prompt(
      'Save query as:',
      `Query ${new Date(item.timestamp).toLocaleString()}`
    )
    if (name?.trim()) {
      addQuery(name.trim(), item.query, item.query_type, null)
    }
  }

  const handleDelete = (id: number) => {
    if (window.confirm('Delete this history item?')) {
      deleteMutation.mutate(id)
    }
  }

  const handleClearAll = () => {
    if (window.confirm('Clear all query history?')) {
      clearMutation.mutate()
    }
  }

  // Flatten all pages into single array
  const allItems = data?.pages.flatMap((page) => page.items) ?? []
  const totalCount = data?.pages[0]?.total ?? 0

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-800">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold">
            History {totalCount > 0 && `(${totalCount.toLocaleString()})`}
          </h3>
          <button
            onClick={handleClearAll}
            disabled={clearMutation.isPending}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded text-red-600 disabled:opacity-50"
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

      {/* History List with Infinite Scroll */}
      <div ref={scrollContainerRef} className="flex-1 overflow-auto">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
          </div>
        ) : error ? (
          <div className="p-4 text-center text-sm text-red-600">
            Error loading history: {error.message}
          </div>
        ) : allItems.length === 0 ? (
          <div className="p-4 text-center text-sm text-gray-500">No query history yet</div>
        ) : (
          <>
            <div className="divide-y divide-gray-200 dark:divide-gray-800">
              {allItems.map((item) => (
                <div
                  key={item.id}
                  className="px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer group"
                  onClick={() => handleHistoryClick(item)}
                >
                  <div className="flex items-start justify-between mb-1">
                    <div className="flex items-center space-x-2">
                      <Clock className="w-3 h-3 text-gray-400" />
                      <span className="text-xs text-gray-500">
                        {formatTimestamp(item.timestamp)}
                      </span>
                      <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 uppercase font-medium">
                        {item.query_type}
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
                          handleDelete(item.id)
                        }}
                        disabled={deleteMutation.isPending}
                        className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-red-600 disabled:opacity-50"
                        title="Delete"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                  <div className="text-sm font-mono text-gray-700 dark:text-gray-300 line-clamp-2">
                    {item.query}
                  </div>
                  {(item.execution_time || item.row_count !== undefined) && (
                    <div className="flex items-center space-x-3 mt-1 text-xs text-gray-400">
                      {item.execution_time && <span>{item.execution_time}ms</span>}
                      {item.row_count !== undefined && (
                        <span>{item.row_count.toLocaleString()} rows</span>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Loading more indicator */}
            {isFetchingNextPage && (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
                <span className="ml-2 text-xs text-gray-500">Loading more...</span>
              </div>
            )}

            {/* No more items indicator */}
            {!hasNextPage && allItems.length > 0 && (
              <div className="py-4 text-center text-xs text-gray-400">
                No more items
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
