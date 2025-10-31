/**
 * Safety Number Banner Component
 *
 * Displays a warning when E2E encryption safety numbers change
 * Critical security feature for detecting MITM attacks
 */

import { useState } from 'react'
import { AlertTriangle, X, Shield } from 'lucide-react'

interface SafetyNumberBannerProps {
  oldNumber: string
  newNumber: string
  userName: string
  onDismiss?: () => void
  onVerify?: () => void
}

export function SafetyNumberBanner({
  oldNumber,
  newNumber,
  userName,
  onDismiss,
  onVerify
}: SafetyNumberBannerProps) {
  const [dismissed, setDismissed] = useState(false)

  const handleDismiss = () => {
    setDismissed(true)
    if (onDismiss) {
      onDismiss()
    }
  }

  const handleVerify = () => {
    if (onVerify) {
      onVerify()
    }
  }

  if (dismissed) return null

  return (
    <div className="mx-4 my-3 p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border-2 border-amber-300 dark:border-amber-700 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-0.5">
          <div className="w-10 h-10 bg-amber-100 dark:bg-amber-900/30 rounded-full flex items-center justify-center">
            <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400" />
          </div>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3 mb-2">
            <h4 className="font-semibold text-amber-900 dark:text-amber-100">
              Safety Number Changed for {userName}
            </h4>
            <button
              onClick={handleDismiss}
              className="flex-shrink-0 p-1 hover:bg-amber-200 dark:hover:bg-amber-800 rounded transition-colors"
              aria-label="Dismiss"
            >
              <X className="w-4 h-4 text-amber-700 dark:text-amber-300" />
            </button>
          </div>

          <p className="text-sm text-amber-700 dark:text-amber-300 mb-3">
            The encryption safety number for this conversation has changed. This could mean {userName}
            reinstalled the app, changed devices, or someone may be intercepting your messages.
          </p>

          <div className="space-y-2 mb-4">
            <div className="p-3 bg-white dark:bg-gray-800 rounded border border-amber-200 dark:border-amber-700">
              <p className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                Previous Safety Number:
              </p>
              <code className="text-xs font-mono bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded
                             text-gray-800 dark:text-gray-200 break-all block">
                {oldNumber}
              </code>
            </div>

            <div className="p-3 bg-white dark:bg-gray-800 rounded border border-amber-200 dark:border-amber-700">
              <p className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                New Safety Number:
              </p>
              <code className="text-xs font-mono bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded
                             text-gray-800 dark:text-gray-200 break-all block">
                {newNumber}
              </code>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              onClick={handleVerify}
              className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm font-medium
                       transition-colors flex items-center gap-2"
            >
              <Shield className="w-4 h-4" />
              Verify Safety Number
            </button>
            <button
              onClick={handleDismiss}
              className="px-4 py-2 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700
                       text-gray-700 dark:text-gray-300 rounded-lg text-sm font-medium border
                       border-gray-300 dark:border-gray-600 transition-colors"
            >
              Dismiss
            </button>
          </div>

          <div className="mt-3 p-3 bg-amber-100/50 dark:bg-amber-900/10 rounded border border-amber-200 dark:border-amber-800">
            <p className="text-xs text-amber-800 dark:text-amber-200">
              <strong>What you should do:</strong> Verify the new safety number matches in person or
              through a trusted channel. If you cannot verify the number, stop sending sensitive messages.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
