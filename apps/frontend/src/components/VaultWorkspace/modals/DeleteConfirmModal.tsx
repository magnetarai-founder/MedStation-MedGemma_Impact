/**
 * Delete Confirmation Modal
 */

import { AlertTriangle, X } from 'lucide-react'
import type { DeleteTarget } from '../types'

interface DeleteConfirmModalProps {
  isOpen: boolean
  deleteTarget: DeleteTarget | null
  onConfirm: () => void
  onClose: () => void
}

export function DeleteConfirmModal({
  isOpen,
  deleteTarget,
  onConfirm,
  onClose
}: DeleteConfirmModalProps) {
  if (!isOpen || !deleteTarget) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-md p-6 border border-gray-200 dark:border-gray-700">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
              <AlertTriangle className="w-6 h-6 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                Delete {deleteTarget.type === 'file' ? 'File' : 'Folder'}
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-0.5">
                This action cannot be undone
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <p className="text-gray-700 dark:text-gray-300 mb-6">
          Are you sure you want to delete <strong className="text-gray-900 dark:text-gray-100">{deleteTarget.name}</strong>?
          {deleteTarget.type === 'folder' && ' All files and subfolders will also be deleted.'}
        </p>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2.5 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 rounded-lg font-medium transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="flex-1 px-4 py-2.5 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  )
}
