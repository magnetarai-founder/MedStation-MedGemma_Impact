/**
 * Stealth Label Modal - Set cover names for documents
 */

import { EyeOff, X } from 'lucide-react'
import { useState, useEffect } from 'react'

interface StealthLabelModalProps {
  isOpen: boolean
  docId: string | null
  currentLabel: string
  realTitle: string
  onSave: (label: string) => void
  onClose: () => void
}

export function StealthLabelModal({ isOpen, docId, currentLabel, realTitle, onSave, onClose }: StealthLabelModalProps) {
  const [label, setLabel] = useState(currentLabel)

  if (!isOpen || !docId) return null

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

  const handleSave = () => {
    onSave(label)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-md p-6 border border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3 mb-4">
          <EyeOff className="w-6 h-6 text-purple-600 dark:text-purple-400" />
          <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Set Stealth Label</h3>
        </div>

        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          Create an innocuous cover name for this document. When "Stealth Labels" is enabled in Security settings, this name will be shown instead of the real title.
        </p>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">Real Title</label>
          <div className="px-3 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-gray-900 dark:text-gray-100 text-sm">
            {realTitle}
          </div>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
            Stealth Label (Cover Name)
          </label>
          <input
            type="text"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="e.g., Grocery List.txt"
            className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            autoFocus
          />
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Leave blank to remove stealth label</p>
        </div>

        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
            Cancel
          </button>
          <button onClick={handleSave} className="flex-1 px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-700 text-white transition-colors">
            Save Label
          </button>
        </div>
      </div>
    </div>
  )
}
