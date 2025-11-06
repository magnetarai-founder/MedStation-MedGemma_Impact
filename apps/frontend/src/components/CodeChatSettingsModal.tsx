import { X, Settings } from 'lucide-react'

interface CodeChatSettingsModalProps {
  isOpen: boolean
  onClose: () => void
}

export function CodeChatSettingsModal({ isOpen, onClose }: CodeChatSettingsModalProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-2xl bg-white dark:bg-gray-900 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <Settings className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              Code Chat Settings
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-8 flex flex-col items-center justify-center min-h-[400px]">
          <div className="text-center space-y-4">
            <div className="w-16 h-16 mx-auto rounded-full bg-gradient-to-br from-primary-100 to-blue-100 dark:from-primary-900/30 dark:to-blue-900/30 flex items-center justify-center">
              <Settings className="w-8 h-8 text-primary-600 dark:text-primary-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Settings Coming Soon
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md">
              Code Chat settings will allow you to configure AI models, context window size,
              temperature, and other preferences specific to your coding workflow.
            </p>
            <div className="pt-4">
              <button
                onClick={onClose}
                className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
              >
                Got it
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
