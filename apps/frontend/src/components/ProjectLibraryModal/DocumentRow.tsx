/**
 * DocumentRow Component
 *
 * Individual document list item with actions (rename, edit, load, delete, download) and tags
 */

import { useState } from 'react'
import { Edit2, ArrowRight, MoreVertical, Trash2, Download } from 'lucide-react'
import type { ProjectDocument } from './types'

interface DocumentRowProps {
  document: ProjectDocument
  isRenaming: boolean
  newName: string
  onStartRename: () => void
  onNameChange: (name: string) => void
  onSaveRename: () => void
  onCancelRename: () => void
  onEdit: () => void
  onLoad: () => void
  onDelete: () => void
  onDownload: () => void
}

export function DocumentRow({
  document,
  isRenaming,
  newName,
  onStartRename,
  onNameChange,
  onSaveRename,
  onCancelRename,
  onEdit,
  onLoad,
  onDelete,
  onDownload,
}: DocumentRowProps) {
  const [showMenu, setShowMenu] = useState(false)

  return (
    <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors group">
      {/* Left: Download icon + Name + Tags */}
      <div className="flex items-center space-x-2 flex-1">
        <button
          onClick={onDownload}
          className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-600 opacity-0 group-hover:opacity-100 transition-opacity"
          title="Download file"
        >
          <Download className="w-4 h-4 text-gray-600 dark:text-gray-300" />
        </button>
        <div className="flex-1">
          {isRenaming ? (
            <input
              type="text"
              value={newName}
              onChange={(e) => onNameChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') onSaveRename()
                if (e.key === 'Escape') onCancelRename()
              }}
              onBlur={onSaveRename}
              autoFocus
              className="px-2 py-1 border border-blue-500 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
            />
          ) : (
            <h4
              className="font-medium text-gray-900 dark:text-gray-100 cursor-text"
              onDoubleClick={onStartRename}
            >
              {document.name}
            </h4>
          )}
          <div className="flex items-center gap-2 mt-1">
            {/* Tags as pills */}
            {document.tags.map((tag, idx) => (
              <span
                key={idx}
                className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400"
              >
                #{tag}
              </span>
            ))}
            {document.tags.length === 0 && (
              <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-1">
                {document.content.slice(0, 100)}...
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center space-x-2 ml-4">
        <button
          onClick={onEdit}
          className="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-600 opacity-0 group-hover:opacity-100 transition-opacity"
          title="Edit"
        >
          <Edit2 className="w-4 h-4 text-gray-600 dark:text-gray-300" />
        </button>
        <button
          onClick={onLoad}
          className="p-2 rounded hover:bg-blue-100 dark:hover:bg-blue-900 opacity-0 group-hover:opacity-100 transition-opacity"
          title="Load to editor"
        >
          <ArrowRight className="w-4 h-4 text-blue-600 dark:text-blue-400" />
        </button>
        <div className="relative">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-600 opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <MoreVertical className="w-4 h-4 text-gray-600 dark:text-gray-300" />
          </button>
          {showMenu && (
            <div className="absolute right-0 mt-2 w-32 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-10">
              <button
                onClick={() => {
                  onDelete()
                  setShowMenu(false)
                }}
                className="w-full px-4 py-2 text-left text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg flex items-center space-x-2"
              >
                <Trash2 className="w-4 h-4" />
                <span>Delete</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
