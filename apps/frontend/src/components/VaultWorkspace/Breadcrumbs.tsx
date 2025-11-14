/**
 * Breadcrumbs Component
 * Path navigation with new folder button
 */

import { Home, Folder, ChevronRight, FolderPlus } from 'lucide-react'
import { getBreadcrumbs } from './helpers'

interface BreadcrumbsProps {
  currentPath: string
  onNavigate: (path: string) => void
  onNewFolder: () => void
}

export function Breadcrumbs({ currentPath, onNavigate, onNewFolder }: BreadcrumbsProps) {
  const breadcrumbs = getBreadcrumbs(currentPath)

  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2 text-sm">
        {breadcrumbs.map((crumb, index) => (
          <div key={crumb.path} className="flex items-center gap-2">
            {index > 0 && <ChevronRight className="w-4 h-4 text-gray-400" />}
            <button
              onClick={() => onNavigate(crumb.path)}
              className={`flex items-center gap-1.5 px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors ${
                crumb.path === currentPath
                  ? 'text-blue-600 dark:text-blue-400 font-medium'
                  : 'text-gray-600 dark:text-gray-400'
              }`}
            >
              {index === 0 ? (
                <Home className="w-4 h-4" />
              ) : (
                <Folder className="w-4 h-4" />
              )}
              <span>{crumb.name}</span>
            </button>
          </div>
        ))}
      </div>

      <button
        onClick={onNewFolder}
        className="px-3 py-1.5 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
      >
        <FolderPlus className="w-4 h-4" />
        New Folder
      </button>
    </div>
  )
}
