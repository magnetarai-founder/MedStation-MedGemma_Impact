/**
 * Folder Context Menu
 */

import { Edit2, Trash2 } from 'lucide-react'

interface FolderContextMenuProps {
  onRename: () => void
  onDelete: () => void
}

export function FolderContextMenu({ onRename, onDelete }: FolderContextMenuProps) {
  return (
    <>
      <button
        onClick={onRename}
        className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3 text-gray-900 dark:text-gray-100"
      >
        <Edit2 className="w-4 h-4" />
        Rename
      </button>
      <div className="border-t border-gray-200 dark:border-gray-700 my-1" />
      <button
        onClick={onDelete}
        className="w-full px-4 py-2 text-left text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-3"
      >
        <Trash2 className="w-4 h-4" />
        Delete
      </button>
    </>
  )
}
