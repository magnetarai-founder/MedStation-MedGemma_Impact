/**
 * ProfileSettingsModal - Thin Modal Wrapper
 *
 * Wraps the ProfileSettings component in a modal shell with backdrop, ESC handling, and close button.
 * All business logic lives in ProfileSettings module - this is just the modal presentation layer.
 */

import { useEffect } from 'react'
import { X } from 'lucide-react'
import { ProfileSettings } from './ProfileSettings'

interface ProfileSettingsModalProps {
  isOpen: boolean
  onClose: () => void
}

export function ProfileSettingsModal({ isOpen, onClose }: ProfileSettingsModalProps) {
  // Handle ESC key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose()
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative w-full max-w-5xl max-h-[90vh] bg-white dark:bg-gray-900 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Profile & Settings
            </h2>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Manage your account and preferences
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-6">
          <ProfileSettings />
        </div>
      </div>
    </div>
  )
}
