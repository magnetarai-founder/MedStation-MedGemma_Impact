import { useState } from 'react'
import { AlertTriangle, Shield } from 'lucide-react'

interface PanicModeModalProps {
  isOpen: boolean
  onClose: () => void
}

export function PanicModeModal({ isOpen, onClose }: PanicModeModalProps) {
  const [needsSecondClick, setNeedsSecondClick] = useState(false)
  const [isTriggering, setIsTriggering] = useState(false)
  const [result, setResult] = useState<any>(null)

  if (!isOpen) return null

  const handleFirstClick = () => {
    setNeedsSecondClick(true)
    // Reset after 5 seconds if not clicked
    setTimeout(() => setNeedsSecondClick(false), 5000)
  }

  const handleTriggerPanic = async () => {
    setIsTriggering(true)

    try {
      const response = await fetch('/api/v1/panic/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          confirmation: 'CONFIRM',
          reason: 'Emergency activation'
        })
      })

      const data = await response.json()
      setResult(data)

      // Clear localStorage
      localStorage.clear()
      sessionStorage.clear()

    } catch (error) {
      console.error('Panic mode failed:', error)
      alert('Panic mode activation failed!')
    } finally {
      setIsTriggering(false)
    }
  }

  const handleClose = () => {
    setNeedsSecondClick(false)
    setResult(null)
    onClose()
  }

  if (result) {
    return (
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="text-green-500" size={24} />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Panic Mode Activated
            </h2>
          </div>

          <div className="space-y-3">
            <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded border border-green-200 dark:border-green-800">
              <p className="text-sm font-medium text-green-900 dark:text-green-100">
                Status: {result.status}
              </p>
              <p className="text-xs text-green-700 dark:text-green-300 mt-1">
                {result.timestamp}
              </p>
            </div>

            <div>
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Actions Taken:
              </p>
              <ul className="space-y-1">
                {result.actions_taken?.map((action: string, i: number) => (
                  <li key={i} className="text-xs text-gray-600 dark:text-gray-400 flex items-center gap-2">
                    <span className="text-green-500">✓</span>
                    {action}
                  </li>
                ))}
              </ul>
            </div>

            {result.errors && result.errors.length > 0 && (
              <div>
                <p className="text-sm font-medium text-red-700 dark:text-red-300 mb-2">
                  Errors:
                </p>
                <ul className="space-y-1">
                  {result.errors.map((error: string, i: number) => (
                    <li key={i} className="text-xs text-red-600 dark:text-red-400">
                      {error}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <button
              onClick={handleClose}
              className="w-full py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6">
        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle className="text-red-500" size={24} />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            🚨 PANIC MODE
          </h2>
        </div>

        <div className="space-y-4">
          <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded border border-red-200 dark:border-red-800">
            <p className="text-sm font-medium text-red-900 dark:text-red-100 mb-2">
              ⚠️ WARNING: This action is IRREVERSIBLE
            </p>
            <p className="text-xs text-red-700 dark:text-red-300">
              This will immediately:
            </p>
            <ul className="mt-2 space-y-1 text-xs text-red-600 dark:text-red-400">
              <li>• Wipe all chat history</li>
              <li>• Delete uploaded documents</li>
              <li>• Close all P2P connections</li>
              <li>• Clear browser cache</li>
              <li>• Secure local databases</li>
            </ul>
          </div>

          {needsSecondClick && (
            <div className="p-3 bg-orange-50 dark:bg-orange-900/20 rounded border border-orange-200 dark:border-orange-800 animate-pulse">
              <p className="text-sm font-medium text-orange-900 dark:text-orange-100">
                ⚠️ Click "CONFIRM WIPE" again to activate
              </p>
              <p className="text-xs text-orange-700 dark:text-orange-300 mt-1">
                This confirmation expires in 5 seconds
              </p>
            </div>
          )}

          <div className="flex gap-2">
            <button
              onClick={handleClose}
              className="flex-1 py-3 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 rounded-lg transition-colors font-medium"
            >
              Cancel
            </button>
            <button
              onClick={needsSecondClick ? handleTriggerPanic : handleFirstClick}
              disabled={isTriggering}
              className={`flex-1 py-3 rounded-lg transition-all font-bold text-white ${
                needsSecondClick
                  ? 'bg-red-700 hover:bg-red-800 animate-pulse scale-105'
                  : 'bg-red-600 hover:bg-red-700'
              } disabled:bg-gray-400 disabled:cursor-not-allowed`}
            >
              {isTriggering ? 'WIPING...' : needsSecondClick ? '🚨 CONFIRM WIPE' : 'ACTIVATE PANIC'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
