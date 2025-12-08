/**
 * Toolbar Component
 * Upload, multi-select, filters, search, sort, view toggle
 */

import {
  Upload, CheckSquare, HardDrive, Trash2, SlidersHorizontal, Pin, Activity,
  Archive, BarChart3, Wifi, WifiOff, Check, X, Download, Search, ArrowUpDown,
  Grid3x3, List
} from 'lucide-react'
import type { ViewMode, SortField, SortDirection, FilterType } from './types'

interface ToolbarProps {
  // File upload
  onUploadClick: () => void

  // Multi-select
  isMultiSelectMode: boolean
  selectedFilesCount: number
  onToggleMultiSelect: () => void
  onSelectAll: () => void
  onDeselectAll: () => void
  onBulkDownload: () => void
  onBulkDelete: () => void

  // Modals
  onStorageClick: () => void
  onTrashClick: () => void
  onPinnedClick: () => void
  onAuditClick: () => void
  onExportClick: () => void
  onAnalyticsClick: () => void

  // Advanced search
  showAdvancedSearch: boolean
  onToggleAdvancedSearch: () => void

  // WebSocket
  wsConnected: boolean
  hasNotifications: boolean

  // Search & filters
  searchQuery: string
  onSearchChange: (query: string) => void
  filterType: FilterType
  onFilterChange: (type: FilterType) => void

  // Sorting
  sortField: SortField
  sortDirection: SortDirection
  onSortFieldChange: (field: SortField) => void
  onToggleSortDirection: () => void

  // View mode
  viewMode: ViewMode
  onViewModeChange: (mode: ViewMode) => void
}

export function Toolbar({
  onUploadClick,
  isMultiSelectMode,
  selectedFilesCount,
  onToggleMultiSelect,
  onSelectAll,
  onDeselectAll,
  onBulkDownload,
  onBulkDelete,
  onStorageClick,
  onTrashClick,
  onPinnedClick,
  onAuditClick,
  onExportClick,
  onAnalyticsClick,
  showAdvancedSearch,
  onToggleAdvancedSearch,
  wsConnected,
  hasNotifications,
  searchQuery,
  onSearchChange,
  filterType,
  onFilterChange,
  sortField,
  sortDirection,
  onSortFieldChange,
  onToggleSortDirection,
  viewMode,
  onViewModeChange
}: ToolbarProps) {
  return (
    <div className="flex items-center gap-3 mb-6 flex-wrap">
      {/* Upload Button */}
      <button
        onClick={onUploadClick}
        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2 flex-shrink-0"
      >
        <Upload className="w-4 h-4" />
        Upload Files
      </button>

      {/* Multi-select Toggle */}
      <button
        onClick={onToggleMultiSelect}
        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 flex-shrink-0 ${
          isMultiSelectMode
            ? 'bg-purple-600 hover:bg-purple-700 text-white'
            : 'bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100'
        }`}
      >
        <CheckSquare className="w-4 h-4" />
        {isMultiSelectMode ? 'Exit Select' : 'Select'}
      </button>

      {/* Storage Dashboard */}
      <button
        onClick={onStorageClick}
        className="px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 flex-shrink-0"
        title="View storage statistics"
      >
        <HardDrive className="w-4 h-4" />
        Storage
      </button>

      {/* Trash Bin Button */}
      <button
        onClick={onTrashClick}
        className="p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-700 dark:text-gray-300"
        title="Trash Bin"
      >
        <Trash2 className="w-4 h-4" />
      </button>

      {/* Advanced Search Button */}
      <button
        onClick={onToggleAdvancedSearch}
        className={`p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded ${showAdvancedSearch ? 'bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300'}`}
        title="Advanced Search"
      >
        <SlidersHorizontal className="w-4 h-4" />
      </button>

      {/* Pinned Files Button */}
      <button
        onClick={onPinnedClick}
        className="p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-700 dark:text-gray-300"
        title="Pinned Files"
      >
        <Pin className="w-4 h-4" />
      </button>

      {/* Audit Log Button */}
      <button
        onClick={onAuditClick}
        className="p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-700 dark:text-gray-300"
        title="Audit Log"
      >
        <Activity className="w-4 h-4" />
      </button>

      {/* Export Button */}
      <button
        onClick={onExportClick}
        className="p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-700 dark:text-gray-300"
        title="Export Vault"
      >
        <Archive className="w-4 h-4" />
      </button>

      {/* Analytics Button */}
      <button
        onClick={onAnalyticsClick}
        className="p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-700 dark:text-gray-300"
        title="Analytics & Insights"
      >
        <BarChart3 className="w-4 h-4" />
      </button>

      {/* WebSocket Status Indicator */}
      <div className="relative">
        <button
          className={`p-2 rounded flex items-center gap-1 ${
            wsConnected
              ? 'text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20'
              : 'text-gray-400 dark:text-gray-600 hover:bg-gray-200 dark:hover:bg-gray-700'
          }`}
          title={wsConnected ? 'Real-time sync active' : 'Real-time sync disconnected'}
        >
          {wsConnected ? (
            <Wifi className="w-4 h-4" />
          ) : (
            <WifiOff className="w-4 h-4" />
          )}
        </button>
        {hasNotifications && (
          <div className="absolute top-0 right-0 w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
        )}
      </div>

      {/* Bulk Actions (shown when in multi-select mode with selections) */}
      {isMultiSelectMode && selectedFilesCount > 0 && (
        <>
          <button
            onClick={onSelectAll}
            className="px-3 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
          >
            <Check className="w-4 h-4" />
            All
          </button>
          <button
            onClick={onDeselectAll}
            className="px-3 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
          >
            <X className="w-4 h-4" />
            None
          </button>
          <button
            onClick={onBulkDownload}
            className="px-3 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Download ({selectedFilesCount})
          </button>
          <button
            onClick={onBulkDelete}
            className="px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
          >
            <Trash2 className="w-4 h-4" />
            Delete ({selectedFilesCount})
          </button>
        </>
      )}

      {/* Search Bar */}
      <div className="relative flex-1 max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          placeholder="Search vault documents..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-amber-500 focus:border-transparent text-sm"
        />
      </div>

      {/* Filter by Type */}
      <select
        value={filterType}
        onChange={(e) => onFilterChange(e.target.value as FilterType)}
        className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-amber-500 focus:border-transparent"
      >
        <option value="all">All Types</option>
        <option value="doc">Documents</option>
        <option value="sheet">Spreadsheets</option>
        <option value="insight">Insights</option>
      </select>

      {/* Sort Files By */}
      <button
        onClick={onToggleSortDirection}
        className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center gap-2"
        title="Toggle sort direction"
      >
        <ArrowUpDown className="w-4 h-4" />
        {sortDirection === 'asc' ? '↑' : '↓'}
      </button>
      <select
        value={sortField}
        onChange={(e) => onSortFieldChange(e.target.value as SortField)}
        className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-amber-500 focus:border-transparent"
      >
        <option value="name">Name</option>
        <option value="date">Date</option>
        <option value="size">Size</option>
        <option value="type">Type</option>
      </select>

      {/* View Toggle */}
      <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
        <button
          onClick={() => onViewModeChange('grid')}
          className={`p-2 rounded ${
            viewMode === 'grid'
              ? 'bg-white dark:bg-gray-700 text-amber-600 dark:text-amber-400 shadow-sm'
              : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
          }`}
        >
          <Grid3x3 className="w-4 h-4" />
        </button>
        <button
          onClick={() => onViewModeChange('list')}
          className={`p-2 rounded ${
            viewMode === 'list'
              ? 'bg-white dark:bg-gray-700 text-amber-600 dark:text-amber-400 shadow-sm'
              : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
          }`}
        >
          <List className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}
