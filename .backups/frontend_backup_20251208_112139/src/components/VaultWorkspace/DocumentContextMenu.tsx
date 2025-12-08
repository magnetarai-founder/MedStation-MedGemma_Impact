/**
 * Document Context Menu (for vault documents)
 */

import { FolderOpen, EyeOff, Lock, AlertTriangle } from 'lucide-react'

interface DocumentContextMenuProps {
  onOpen: () => void
  onSetStealthLabel: () => void
  onMoveToRegular: () => void
  onDelete: () => void
}

export function DocumentContextMenu({
  onOpen,
  onSetStealthLabel,
  onMoveToRegular,
  onDelete
}: DocumentContextMenuProps) {
  return (
    <>
      <button
        onClick={onOpen}
        className="w-full px-4 py-2 text-left hover:bg-blue-50 dark:hover:bg-blue-900/20 flex items-center gap-3 text-sm text-gray-900 dark:text-gray-100"
      >
        <FolderOpen className="w-4 h-4 text-blue-600 dark:text-blue-400" />
        <span>Open</span>
      </button>
      <button
        onClick={onSetStealthLabel}
        className="w-full px-4 py-2 text-left hover:bg-purple-50 dark:hover:bg-purple-900/20 flex items-center gap-3 text-sm text-gray-900 dark:text-gray-100"
      >
        <EyeOff className="w-4 h-4 text-purple-600 dark:text-purple-400" />
        <span>Set Stealth Label</span>
      </button>
      <button
        onClick={onMoveToRegular}
        className="w-full px-4 py-2 text-left hover:bg-amber-50 dark:hover:bg-amber-900/20 flex items-center gap-3 text-sm text-gray-900 dark:text-gray-100"
      >
        <Lock className="w-4 h-4 text-amber-600 dark:text-amber-400" />
        <span>Move to Regular Docs</span>
      </button>
      <div className="border-t border-gray-200 dark:border-gray-700 my-1" />
      <button
        onClick={onDelete}
        className="w-full px-4 py-2 text-left hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-3 text-sm"
      >
        <AlertTriangle className="w-4 h-4 text-red-600 dark:text-red-400" />
        <span className="text-red-700 dark:text-red-300">Delete</span>
      </button>
    </>
  )
}
