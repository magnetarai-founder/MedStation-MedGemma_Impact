import { useState } from 'react'
import { Search, X } from 'lucide-react'
import axios from 'axios'
import toast from 'react-hot-toast'

interface AdvancedSearchPanelProps {
  isOpen: boolean
  vaultMode: string
  onClose: () => void
  onResults: (results: any[]) => void
}

export function AdvancedSearchPanel({ isOpen, vaultMode, onClose, onResults }: AdvancedSearchPanelProps) {
  const [searchFilters, setSearchFilters] = useState({
    query: '',
    mimeType: '',
    tags: [],
    dateFrom: '',
    dateTo: '',
    minSize: '',
    maxSize: '',
    folderPath: ''
  })

  const handleAdvancedSearch = async () => {
    try {
      const params = new URLSearchParams({
        vault_type: vaultMode,
        limit: '100',
        offset: '0',
        ...(searchFilters.query && { query: searchFilters.query }),
        ...(searchFilters.mimeType && { mime_type: searchFilters.mimeType }),
        ...(searchFilters.dateFrom && { date_from: searchFilters.dateFrom }),
        ...(searchFilters.dateTo && { date_to: searchFilters.dateTo }),
        ...(searchFilters.minSize && { min_size: searchFilters.minSize }),
        ...(searchFilters.maxSize && { max_size: searchFilters.maxSize }),
        ...(searchFilters.folderPath && { folder_path: searchFilters.folderPath })
      })

      const response = await axios.get(`/api/v1/vault/search?${params}`)
      // Backend now returns {results, total, limit, offset, has_more}
      onResults(response.data.results || [])
      const total = response.data.total || 0
      const shown = response.data.results?.length || 0
      toast.success(`Found ${total} file(s)${total > shown ? ` (showing first ${shown})` : ''}`)
    } catch (error) {
      console.error('Search failed:', error)
      toast.error('Advanced search failed')
      onResults([])
    }
  }

  const handleClearFilters = () => {
    setSearchFilters({
      query: '',
      mimeType: '',
      tags: [],
      dateFrom: '',
      dateTo: '',
      minSize: '',
      maxSize: '',
      folderPath: ''
    })
    onResults([])
  }

  if (!isOpen) return null

  return (
    <div className="bg-gray-100 dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-lg p-4 mb-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold flex items-center gap-2 text-gray-900 dark:text-gray-100">
          <Search className="w-5 h-5" />
          Advanced Search
        </h3>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-200 dark:hover:bg-zinc-700 rounded"
          title="Close"
        >
          <X className="w-4 h-4 text-gray-500" />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Text Query */}
        <div>
          <label className="block text-sm mb-1 text-gray-700 dark:text-gray-300">Search Query</label>
          <input
            type="text"
            value={searchFilters.query}
            onChange={(e) => setSearchFilters({ ...searchFilters, query: e.target.value })}
            className="w-full px-3 py-2 bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded text-gray-900 dark:text-gray-100"
            placeholder="filename..."
          />
        </div>

        {/* MIME Type */}
        <div>
          <label className="block text-sm mb-1 text-gray-700 dark:text-gray-300">File Type</label>
          <select
            value={searchFilters.mimeType}
            onChange={(e) => setSearchFilters({ ...searchFilters, mimeType: e.target.value })}
            className="w-full px-3 py-2 bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded text-gray-900 dark:text-gray-100"
          >
            <option value="">All Types</option>
            <option value="image">Images</option>
            <option value="video">Videos</option>
            <option value="audio">Audio</option>
            <option value="text">Text</option>
            <option value="application/pdf">PDF</option>
          </select>
        </div>

        {/* Date Range */}
        <div>
          <label className="block text-sm mb-1 text-gray-700 dark:text-gray-300">From Date</label>
          <input
            type="date"
            value={searchFilters.dateFrom}
            onChange={(e) => setSearchFilters({ ...searchFilters, dateFrom: e.target.value })}
            className="w-full px-3 py-2 bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded text-gray-900 dark:text-gray-100"
          />
        </div>

        <div>
          <label className="block text-sm mb-1 text-gray-700 dark:text-gray-300">To Date</label>
          <input
            type="date"
            value={searchFilters.dateTo}
            onChange={(e) => setSearchFilters({ ...searchFilters, dateTo: e.target.value })}
            className="w-full px-3 py-2 bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded text-gray-900 dark:text-gray-100"
          />
        </div>

        {/* Size Range */}
        <div>
          <label className="block text-sm mb-1 text-gray-700 dark:text-gray-300">Min Size (bytes)</label>
          <input
            type="number"
            value={searchFilters.minSize}
            onChange={(e) => setSearchFilters({ ...searchFilters, minSize: e.target.value })}
            className="w-full px-3 py-2 bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded text-gray-900 dark:text-gray-100"
            placeholder="0"
          />
        </div>

        <div>
          <label className="block text-sm mb-1 text-gray-700 dark:text-gray-300">Max Size (bytes)</label>
          <input
            type="number"
            value={searchFilters.maxSize}
            onChange={(e) => setSearchFilters({ ...searchFilters, maxSize: e.target.value })}
            className="w-full px-3 py-2 bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded text-gray-900 dark:text-gray-100"
            placeholder="unlimited"
          />
        </div>
      </div>

      {/* Applied Filters Display */}
      {(searchFilters.query || searchFilters.mimeType || searchFilters.dateFrom || searchFilters.dateTo || searchFilters.minSize || searchFilters.maxSize) && (
        <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded">
          <p className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-2">Active Filters:</p>
          <div className="flex flex-wrap gap-2 text-xs">
            {searchFilters.query && (
              <span className="px-2 py-1 bg-white dark:bg-zinc-900 border border-blue-300 dark:border-blue-700 rounded text-gray-900 dark:text-gray-100">
                Query: "{searchFilters.query}"
              </span>
            )}
            {searchFilters.mimeType && (
              <span className="px-2 py-1 bg-white dark:bg-zinc-900 border border-blue-300 dark:border-blue-700 rounded text-gray-900 dark:text-gray-100">
                Type: {searchFilters.mimeType}
              </span>
            )}
            {searchFilters.dateFrom && (
              <span className="px-2 py-1 bg-white dark:bg-zinc-900 border border-blue-300 dark:border-blue-700 rounded text-gray-900 dark:text-gray-100">
                From: {searchFilters.dateFrom}
              </span>
            )}
            {searchFilters.dateTo && (
              <span className="px-2 py-1 bg-white dark:bg-zinc-900 border border-blue-300 dark:border-blue-700 rounded text-gray-900 dark:text-gray-100">
                To: {searchFilters.dateTo}
              </span>
            )}
            {searchFilters.minSize && (
              <span className="px-2 py-1 bg-white dark:bg-zinc-900 border border-blue-300 dark:border-blue-700 rounded text-gray-900 dark:text-gray-100">
                Min: {searchFilters.minSize}B
              </span>
            )}
            {searchFilters.maxSize && (
              <span className="px-2 py-1 bg-white dark:bg-zinc-900 border border-blue-300 dark:border-blue-700 rounded text-gray-900 dark:text-gray-100">
                Max: {searchFilters.maxSize}B
              </span>
            )}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-2 mt-4">
        <button
          onClick={handleAdvancedSearch}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded flex items-center gap-2"
        >
          <Search className="w-4 h-4" />
          Search
        </button>
        <button
          onClick={handleClearFilters}
          className="px-4 py-2 bg-gray-300 dark:bg-zinc-700 hover:bg-gray-400 dark:hover:bg-zinc-600 text-gray-900 dark:text-gray-100 rounded"
        >
          Clear
        </button>
      </div>
    </div>
  )
}
