/**
 * DeleteConfirmDialog Component
 *
 * Confirmation dialog for deleting a saved query
 */

import { useState } from 'react'

interface DeleteConfirmDialogProps {
  queryName: string
  onConfirm: () => void
  onCancel: () => void
}

export function DeleteConfirmDialog({ queryName, onConfirm, onCancel }: DeleteConfirmDialogProps) {
  const [confirmText, setConfirmText] = useState('')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/70" onClick={onCancel} />
      <div className="relative bg-white dark:bg-gray-900 rounded-xl p-6 max-w-md shadow-2xl">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Delete Query
        </h3>
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          You are about to delete <strong>{queryName}</strong>. This action cannot be undone.
        </p>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          Type <strong>DELETE</strong> to confirm:
        </p>
        <input
          type="text"
          value={confirmText}
          onChange={(e) => setConfirmText(e.target.value)}
          placeholder="DELETE"
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 mb-4"
        />
        <div className="flex justify-end space-x-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={confirmText !== 'DELETE'}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  )
}
