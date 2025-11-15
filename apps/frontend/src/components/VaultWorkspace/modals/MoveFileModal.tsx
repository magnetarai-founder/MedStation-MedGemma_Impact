/**
 * Move File Modal
 */

import { useEffect } from 'react'
import { FolderInput, X, Home, Folder } from 'lucide-react'
import type { MoveTarget, VaultFolder } from '../types'

interface MoveFileModalProps {
  isOpen: boolean
  moveTarget: MoveTarget | null
  folders: VaultFolder[]
  onMove: (path: string) => void
  onClose: () => void
}

export function MoveFileModal({ isOpen, moveTarget, folders, onMove, onClose }: MoveFileModalProps) {
  if (!isOpen || !moveTarget) return null

  // Handle Escape key to close modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-md p-6 border border-gray-200 dark:border-gray-700">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center">
              <FolderInput className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                Move File
              </h3>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          Select a folder to move <strong>{moveTarget.filename}</strong> to:
        </p>

        <div className="max-h-64 overflow-y-auto mb-4 border border-gray-200 dark:border-gray-700 rounded-lg">
          <button
            onClick={() => onMove('/')}
            className="w-full px-4 py-2 text-left hover:bg-blue-50 dark:hover:bg-blue-900/20 flex items-center gap-2 text-gray-900 dark:text-gray-100"
          >
            <Home className="w-4 h-4" />
            <span>Root</span>
          </button>
          {folders.map((folder) => (
            <button
              key={folder.id}
              onClick={() => onMove(folder.folder_path)}
              disabled={folder.folder_path === moveTarget.currentPath}
              className="w-full px-4 py-2 text-left hover:bg-blue-50 dark:hover:bg-blue-900/20 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed text-gray-900 dark:text-gray-100"
            >
              <Folder className="w-4 h-4" />
              <span>{folder.folder_path}</span>
            </button>
          ))}
        </div>

        <button
          onClick={onClose}
          className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}
