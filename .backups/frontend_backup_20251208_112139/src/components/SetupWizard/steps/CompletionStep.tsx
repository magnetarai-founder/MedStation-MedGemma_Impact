import { useState } from 'react'
import { CheckCircle, Sparkles, User, Server, Package, Star, Loader2 } from 'lucide-react'
import { SetupWizardState } from '../SetupWizard'
import { setupWizardApi } from '../../../lib/setupWizardApi'

interface StepProps {
  wizardState: SetupWizardState
  updateWizardState: (updates: Partial<SetupWizardState>) => void
  onNext: () => void
  onBack?: () => void
  onComplete?: () => void
}

export default function CompletionStep(props: StepProps) {
  const [enableAutoPreload, setEnableAutoPreload] = useState(false)
  const [isCompleting, setIsCompleting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFinish = async () => {
    setIsCompleting(true)
    setError(null)

    try {
      // Mark setup as complete via API
      await setupWizardApi.completeSetup()

      // Store autoPreloadModel preference
      // This will be handled by App.tsx after setup completes
      if (enableAutoPreload) {
        localStorage.setItem('setup_autoPreloadModel', 'true')
      }

      // Call completion callback
      if (props.onComplete) {
        props.onComplete()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to complete setup')
    } finally {
      setIsCompleting(false)
    }
  }

  const selectedModels = props.wizardState.selectedModels || []
  const hotSlots = props.wizardState.hotSlots || {}
  const assignedSlots = Object.values(hotSlots).filter(m => m !== null).length

  return (
    <div className="max-w-2xl mx-auto p-8">
      {/* Success Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-20 h-20 bg-green-100 dark:bg-green-900/30 rounded-full mb-4">
          <Sparkles className="w-10 h-10 text-green-600 dark:text-green-400" />
        </div>
        <h2 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          Setup Complete!
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          MagnetarStudio is ready for use. Here's what we've configured:
        </p>
      </div>

      {/* Setup Summary */}
      <div className="space-y-3 mb-8">
        {/* Account Created */}
        {props.wizardState.accountCreated && (
          <div className="flex items-center gap-3 p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
            <div className="flex items-center justify-center w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-full">
              <User className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            <div className="flex-1">
              <p className="font-medium text-gray-900 dark:text-gray-100">Local Account Created</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Super admin account with full privileges
              </p>
            </div>
            <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
          </div>
        )}

        {/* Ollama Ready */}
        {props.wizardState.ollamaRunning && (
          <div className="flex items-center gap-3 p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
            <div className="flex items-center justify-center w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-full">
              <Server className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="flex-1">
              <p className="font-medium text-gray-900 dark:text-gray-100">Ollama Service Running</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Local AI inference ready
              </p>
            </div>
            <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
          </div>
        )}

        {/* Models Downloaded */}
        {selectedModels.length > 0 && (
          <div className="flex items-center gap-3 p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
            <div className="flex items-center justify-center w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-full">
              <Package className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div className="flex-1">
              <p className="font-medium text-gray-900 dark:text-gray-100">
                {selectedModels.length} Model{selectedModels.length > 1 ? 's' : ''} Downloaded
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {selectedModels.slice(0, 2).join(', ')}
                {selectedModels.length > 2 && ` +${selectedModels.length - 2} more`}
              </p>
            </div>
            <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
          </div>
        )}

        {/* Hot Slots Configured */}
        {assignedSlots > 0 && (
          <div className="flex items-center gap-3 p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
            <div className="flex items-center justify-center w-10 h-10 bg-yellow-100 dark:bg-yellow-900/30 rounded-full">
              <Star className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
            </div>
            <div className="flex-1">
              <p className="font-medium text-gray-900 dark:text-gray-100">
                {assignedSlots} Hot Slot{assignedSlots > 1 ? 's' : ''} Configured
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Quick-access favorites ready
              </p>
            </div>
            <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
          </div>
        )}
      </div>

      {/* Optional Settings */}
      <div className="mb-8 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
        <h3 className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-3">
          Optional: Auto-preload Default Model
        </h3>
        <div className="flex items-start gap-3">
          <input
            id="enableAutoPreload"
            type="checkbox"
            checked={enableAutoPreload}
            onChange={(e) => setEnableAutoPreload(e.target.checked)}
            className="mt-1 w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
          />
          <label htmlFor="enableAutoPreload" className="flex-1">
            <p className="text-sm text-blue-800 dark:text-blue-200">
              Automatically load your default model 3 seconds after login
            </p>
            <p className="text-xs text-blue-700 dark:text-blue-300 mt-1">
              You can change this later in Settings → Chat → Auto-preload default model
            </p>
          </label>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3">
        {props.onBack && (
          <button
            onClick={props.onBack}
            disabled={isCompleting}
            className="flex-1 px-6 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Back
          </button>
        )}
        <button
          onClick={handleFinish}
          disabled={isCompleting}
          className="flex-1 px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-medium"
        >
          {isCompleting ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Finishing Setup...
            </>
          ) : (
            <>
              <Sparkles className="w-5 h-5" />
              Launch MagnetarStudio
            </>
          )}
        </button>
      </div>
    </div>
  )
}
