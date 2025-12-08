import { useState, useEffect } from 'react'
import { Star, CheckCircle, Info } from 'lucide-react'
import { SetupWizardState } from '../SetupWizard'
import { userModelsApi, HotSlots } from '../../../lib/userModelsApi'
import { setupWizardApi } from '../../../lib/setupWizardApi'

interface StepProps {
  wizardState: SetupWizardState
  updateWizardState: (updates: Partial<SetupWizardState>) => void
  onNext: () => void
  onBack?: () => void
  onComplete?: () => void
}

export default function HotSlotsStep(props: StepProps) {
  const [slots, setSlots] = useState<HotSlots>({
    1: null,
    2: null,
    3: null,
    4: null
  })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [installedModels, setInstalledModels] = useState<string[]>([])

  const selectedModels = props.wizardState.selectedModels || []

  useEffect(() => {
    // Load installed models
    loadInstalledModels()

    // Load existing hot slots (if user has any)
    loadExistingHotSlots()
  }, [])

  const loadInstalledModels = async () => {
    try {
      const result = await setupWizardApi.getInstalledModels()
      setInstalledModels(result.models.map((m: any) => m.name))
    } catch (err) {
      console.error('Failed to load installed models:', err)
    }
  }

  const loadExistingHotSlots = async () => {
    try {
      // Try to load existing hot slots for this user
      const result = await userModelsApi.getHotSlots()
      if (result.slots) {
        setSlots(result.slots)
      }
    } catch (err) {
      // If error (e.g., user not logged in yet), use empty slots
      console.debug('No existing hot slots found:', err)
    }
  }

  const handleSlotChange = (slotNum: number, modelName: string) => {
    setSlots(prev => ({
      ...prev,
      [slotNum]: modelName || null
    }) as HotSlots)
  }

  const handleNext = async () => {
    setIsLoading(true)
    setError(null)

    try {
      // Save hot slots configuration using per-user API
      await userModelsApi.updateHotSlots(slots)

      // Store in wizard state
      props.updateWizardState({
        hotSlotsConfigured: true,
        hotSlots: slots
      })

      props.onNext()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to configure hot slots')
    } finally {
      setIsLoading(false)
    }
  }

  // Available models = only those that were successfully downloaded
  // Filter selected models by installed models to avoid assigning non-downloaded models
  const availableModels = selectedModels.length > 0
    ? selectedModels.filter(m => installedModels.includes(m))
    : installedModels

  const assignedCount = Object.values(slots).filter(m => m !== null).length

  return (
    <div className="max-w-2xl mx-auto p-8">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 dark:bg-primary-900/30 rounded-full mb-4">
          <Star className="w-8 h-8 text-primary-600 dark:text-primary-400" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          Configure Hot Slots
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          Assign up to 4 favorite models for quick switching
        </p>
      </div>

      {/* Info Banner */}
      <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-blue-900 dark:text-blue-100">What are hot slots?</p>
            <p className="text-xs text-blue-800 dark:text-blue-200 mt-1">
              Hot slots are quick-access favorites for your most-used models. You can assign/eject them anytime from the Model Management sidebar.
            </p>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {/* Slot Assignment Summary */}
      <div className="mb-6 p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600 dark:text-gray-400">Slots Assigned</span>
          <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
            {assignedCount} of 4
          </span>
        </div>
      </div>

      {/* Hot Slot Selectors */}
      <div className="space-y-4 mb-8">
        {[1, 2, 3, 4].map(slotNum => (
          <div
            key={slotNum}
            className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg"
          >
            <label className="block mb-2">
              <div className="flex items-center gap-2 mb-2">
                <Star className={`w-4 h-4 ${slots[slotNum] ? 'text-yellow-500 fill-yellow-500' : 'text-gray-400'}`} />
                <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  Hot Slot {slotNum}
                </span>
              </div>
              <select
                value={slots[slotNum] || ''}
                onChange={(e) => handleSlotChange(slotNum, e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="">-- Not assigned --</option>
                {availableModels.map(modelName => (
                  <option key={modelName} value={modelName}>
                    {modelName}
                  </option>
                ))}
              </select>
            </label>
          </div>
        ))}
      </div>

      {/* No Models Warning */}
      {availableModels.length === 0 && (
        <div className="mb-6 p-4 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg">
          <p className="text-sm text-orange-800 dark:text-orange-200">
            No models available to assign. You can configure hot slots later from the Model Management sidebar.
          </p>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3">
        {props.onBack && (
          <button
            onClick={props.onBack}
            disabled={isLoading}
            className="flex-1 px-6 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Back
          </button>
        )}
        <button
          onClick={handleNext}
          disabled={isLoading}
          className="flex-1 px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <CheckCircle className="w-4 h-4" />
              {assignedCount > 0 ? `Continue with ${assignedCount} slot${assignedCount > 1 ? 's' : ''}` : 'Skip Hot Slots'}
            </>
          )}
        </button>
      </div>
    </div>
  )
}
