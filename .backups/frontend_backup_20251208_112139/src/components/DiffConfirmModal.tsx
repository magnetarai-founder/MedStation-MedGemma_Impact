import React, { useEffect } from 'react'

interface DiffConfirmModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  diffText: string
  filePath: string
  conflictWarning?: string
  truncated?: boolean
  truncationMessage?: string
}

export function DiffConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  diffText,
  filePath,
  conflictWarning,
  truncated,
  truncationMessage,
}: DiffConfirmModalProps) {
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

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-lg w-full max-w-4xl max-h-[80vh] flex flex-col shadow-xl">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
            Review Changes: {filePath}
          </h2>
          {conflictWarning && (
            <div className="mt-2 text-sm text-orange-600 dark:text-orange-400">
              ⚠️ {conflictWarning}
            </div>
          )}
          {truncated && (
            <div className="mt-2 text-sm text-blue-600 dark:text-blue-400">
              ℹ️ {truncationMessage || 'Diff truncated for size - showing partial preview'}
            </div>
          )}
        </div>

        <div className="flex-1 overflow-auto p-6">
          <pre className="text-xs font-mono bg-gray-50 dark:bg-gray-900 p-4 rounded overflow-x-auto text-gray-800 dark:text-gray-200">
            {diffText || 'No changes'}
          </pre>
        </div>

        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm bg-gray-200 dark:bg-gray-700 rounded text-gray-800 dark:text-gray-200 hover:bg-gray-300 dark:hover:bg-gray-600"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 text-sm bg-primary-600 text-white rounded hover:bg-primary-700"
          >
            Confirm Save
          </button>
        </div>
      </div>
    </div>
  )
}
