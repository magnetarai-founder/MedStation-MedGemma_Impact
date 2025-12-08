/**
 * FolderGrid Component
 * Displays folders with drag-drop support
 */

import { Folder, MoreVertical, Clock } from 'lucide-react'
import { formatDate } from './helpers'
import type { VaultFolder } from './types'

interface FolderGridProps {
  folders: VaultFolder[]
  dropTargetFolder: string | null
  onFolderClick: (path: string) => void
  onFolderContextMenu: (e: React.MouseEvent, folder: VaultFolder) => void
  onFolderDragOver: (e: React.DragEvent, path: string) => void
  onFolderDragLeave: () => void
  onFolderDrop: (e: React.DragEvent, path: string) => void
}

export function FolderGrid({
  folders,
  dropTargetFolder,
  onFolderClick,
  onFolderContextMenu,
  onFolderDragOver,
  onFolderDragLeave,
  onFolderDrop
}: FolderGridProps) {
  if (folders.length === 0) return null

  return (
    <>
      {folders.map((folder) => {
        const isDropTarget = dropTargetFolder === folder.folder_path

        return (
          <div
            key={folder.id}
            onClick={() => onFolderClick(folder.folder_path)}
            onContextMenu={(e) => onFolderContextMenu(e, folder)}
            onDragOver={(e) => onFolderDragOver(e, folder.folder_path)}
            onDragLeave={onFolderDragLeave}
            onDrop={(e) => onFolderDrop(e, folder.folder_path)}
            className={`group relative p-4 bg-white dark:bg-gray-800 border-2 rounded-lg hover:shadow-lg transition-all cursor-pointer ${
              isDropTarget
                ? 'border-green-500 dark:border-green-400 bg-green-50 dark:bg-green-900/20'
                : 'border-gray-200 dark:border-gray-700 hover:border-blue-500 dark:hover:border-blue-400'
            }`}
          >
            <div className="flex items-start justify-between mb-3">
              <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                <Folder className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onFolderContextMenu(e as any, folder)
                }}
                className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-opacity"
              >
                <MoreVertical className="w-4 h-4 text-gray-500" />
              </button>
            </div>
            <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-1 truncate">
              {folder.folder_name}
            </h3>
            <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
              <Clock className="w-3 h-3" />
              <span>{formatDate(folder.created_at)}</span>
            </div>
          </div>
        )
      })}
    </>
  )
}
