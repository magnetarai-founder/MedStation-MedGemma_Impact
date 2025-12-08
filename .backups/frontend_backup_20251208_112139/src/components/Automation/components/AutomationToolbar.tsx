import { Search, ArrowUpDown, Grid, List, Star, Trash2 } from 'lucide-react'
import type { SortOption, ViewLayout } from '../types'

interface AutomationToolbarProps {
  searchQuery: string
  onSearchChange: (query: string) => void
  sortBy: SortOption
  onSortChange: (sort: SortOption) => void
  viewLayout: ViewLayout
  onViewLayoutChange: (layout: ViewLayout) => void
  showFavoritesOnly: boolean
  onToggleFavorites: () => void
  isEditMode: boolean
  selectedCount: number
  onBulkDelete?: () => void
}

export function AutomationToolbar({
  searchQuery,
  onSearchChange,
  sortBy,
  onSortChange,
  viewLayout,
  onViewLayoutChange,
  showFavoritesOnly,
  onToggleFavorites,
  isEditMode,
  selectedCount,
  onBulkDelete
}: AutomationToolbarProps) {
  return (
    <div className="space-y-3">
      {/* Main toolbar */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Search */}
        <div className="flex-1 min-w-[200px]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search workflows..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
        </div>

        {/* Sort */}
        <div className="relative">
          <select
            value={sortBy}
            onChange={(e) => onSortChange(e.target.value as SortOption)}
            className="pl-3 pr-10 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500 appearance-none cursor-pointer"
          >
            <option value="recent">Recent</option>
            <option value="name">Name</option>
            <option value="nodes">Steps</option>
            <option value="favorites">Favorites</option>
          </select>
          <ArrowUpDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
        </div>

        {/* View Layout Toggle */}
        <div className="flex items-center gap-1 border border-gray-300 dark:border-gray-600 rounded-lg p-1">
          <button
            onClick={() => onViewLayoutChange('grid')}
            className={`p-1.5 rounded ${
              viewLayout === 'grid'
                ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
            title="Grid view"
          >
            <Grid className="w-4 h-4" />
          </button>
          <button
            onClick={() => onViewLayoutChange('list')}
            className={`p-1.5 rounded ${
              viewLayout === 'list'
                ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
            title="List view"
          >
            <List className="w-4 h-4" />
          </button>
        </div>

        {/* Favorites Toggle */}
        <button
          onClick={onToggleFavorites}
          className={`px-3 py-2 rounded-lg flex items-center gap-2 transition-colors ${
            showFavoritesOnly
              ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 border border-yellow-300 dark:border-yellow-700'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:bg-gray-200 dark:hover:bg-gray-700'
          }`}
          title="Show favorites only"
        >
          <Star className={`w-4 h-4 ${showFavoritesOnly ? 'fill-current' : ''}`} />
          <span className="text-sm font-medium">Favorites</span>
        </button>
      </div>

      {/* Bulk actions bar (when in edit mode) */}
      {isEditMode && selectedCount > 0 && (
        <div className="flex items-center justify-between p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <span className="text-sm font-medium text-blue-900 dark:text-blue-100">
            {selectedCount} selected {selectedCount === 10 && '(max)'}
          </span>
          <button
            onClick={onBulkDelete}
            className="flex items-center gap-2 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Delete Selected
          </button>
        </div>
      )}
    </div>
  )
}
