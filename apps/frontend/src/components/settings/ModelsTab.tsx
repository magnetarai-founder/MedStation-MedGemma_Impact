/**
 * Models Tab - Settings
 *
 * Per-user model preferences and hot slots management.
 * Allows users to control which models they see and assign favorites.
 */

import { useState, useEffect } from 'react'
import { Package, Eye, EyeOff, Star, AlertTriangle, Loader2, Check, X } from 'lucide-react'
import { useUserModelPrefsStore } from '../../stores/userModelPrefsStore'
import { userModelsApi, HotSlots } from '../../lib/userModelsApi'
import toast from 'react-hot-toast'

export default function ModelsTab() {
  const {
    catalog,
    catalogLoading,
    catalogError,
    preferences,
    preferencesLoading,
    hotSlots,
    hotSlotsLoading,
    loadAll,
    toggleModelVisibility,
    assignHotSlot,
    getVisibleModels
  } = useUserModelPrefsStore()

  const [saving, setSaving] = useState(false)
  const [confirmHideSlottedModel, setConfirmHideSlottedModel] = useState<{
    modelName: string
    slotNumber: number
  } | null>(null)

  // Load all data on mount
  useEffect(() => {
    loadAll()
  }, [])

  // Check if model is in a hot slot
  const getModelSlot = (modelName: string): number | null => {
    for (const [slotNum, model] of Object.entries(hotSlots)) {
      if (model === modelName) {
        return parseInt(slotNum)
      }
    }
    return null
  }

  // Handle visibility toggle with hot slot check
  const handleToggleVisibility = async (modelName: string) => {
    const isCurrentlyVisible = preferences.find(p => p.model_name === modelName)?.visible ?? true
    const slotNumber = getModelSlot(modelName)

    // If hiding and model is in a slot, show confirmation
    if (isCurrentlyVisible && slotNumber !== null) {
      setConfirmHideSlottedModel({ modelName, slotNumber })
      return
    }

    // Toggle visibility
    try {
      setSaving(true)
      await toggleModelVisibility(modelName)
      toast.success(isCurrentlyVisible ? 'Model hidden' : 'Model visible')
    } catch (error) {
      toast.error('Failed to update visibility')
      console.error(error)
    } finally {
      setSaving(false)
    }
  }

  // Confirm hiding slotted model
  const handleConfirmHideSlotted = async () => {
    if (!confirmHideSlottedModel) return

    const { modelName, slotNumber } = confirmHideSlottedModel

    try {
      setSaving(true)

      // Clear hot slot first
      await assignHotSlot(slotNumber as (1 | 2 | 3 | 4), null)

      // Then hide model
      await toggleModelVisibility(modelName)

      toast.success(`Model hidden and removed from Slot ${slotNumber}`)
      setConfirmHideSlottedModel(null)
    } catch (error) {
      toast.error('Failed to update model')
      console.error(error)
    } finally {
      setSaving(false)
    }
  }

  // Handle hot slot assignment
  const handleAssignSlot = async (slotNumber: 1 | 2 | 3 | 4, modelName: string | null) => {
    try {
      setSaving(true)
      await assignHotSlot(slotNumber, modelName)
      toast.success(modelName ? `Assigned to Slot ${slotNumber}` : `Slot ${slotNumber} cleared`)
    } catch (error) {
      toast.error('Failed to update hot slot')
      console.error(error)
    } finally {
      setSaving(false)
    }
  }

  const loading = catalogLoading || preferencesLoading || hotSlotsLoading
  const error = catalogError

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex items-center gap-3 text-gray-500 dark:text-gray-400">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span>Loading model settings...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" />
          <h4 className="text-sm font-semibold text-red-900 dark:text-red-100">
            Error Loading Models
          </h4>
        </div>
        <p className="text-xs text-red-800 dark:text-red-200 mt-1">{error}</p>
      </div>
    )
  }

  const visibleModels = getVisibleModels()
  const visibleModelNames = new Set(visibleModels.map(m => m.model_name))

  return (
    <div className="space-y-6">
      {/* Confirmation Dialog */}
      {confirmHideSlottedModel && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md border border-gray-200 dark:border-gray-700">
            <div className="flex items-start gap-3 mb-4">
              <AlertTriangle className="w-6 h-6 text-orange-600 dark:text-orange-400 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Model in Hot Slot
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  <strong>{confirmHideSlottedModel.modelName}</strong> is assigned to Slot {confirmHideSlottedModel.slotNumber}.
                  Hiding it will also clear this slot.
                </p>
              </div>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirmHideSlottedModel(null)}
                className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmHideSlotted}
                disabled={saving}
                className="flex-1 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {saving ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Updating...
                  </>
                ) : (
                  'Hide & Clear Slot'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <Package className="w-5 h-5 text-primary-600 dark:text-primary-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            My Models
          </h3>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Choose which models you want to see in your model selector. {visibleModels.length} of {catalog.length} visible.
        </p>
      </div>

      {/* Info Banner */}
      <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
        <p className="text-sm text-blue-800 dark:text-blue-200">
          💡 <strong>Personal Preferences:</strong> These settings are personal to you.
          Other users on this device can have different preferences.
        </p>
      </div>

      {/* Model List */}
      <div className="space-y-3">
        {catalog.length === 0 ? (
          <div className="text-center py-12">
            <Package className="w-16 h-16 text-gray-400 dark:text-gray-600 mx-auto mb-4" />
            <p className="text-gray-600 dark:text-gray-400">
              No models found. Make sure Ollama is running and has models installed.
            </p>
          </div>
        ) : (
          catalog.map((model) => {
            const isVisible = visibleModelNames.has(model.model_name)
            const slotNumber = getModelSlot(model.model_name)
            const isInstalled = model.status === 'installed'

            return (
              <div
                key={model.model_name}
                className={`p-4 rounded-lg border-2 transition-all ${
                  isVisible
                    ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                    : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h4 className="font-medium text-gray-900 dark:text-gray-100">
                        {model.model_name}
                      </h4>

                      {/* Status Badge */}
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full ${
                          isInstalled
                            ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                            : 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300'
                        }`}
                      >
                        {model.status}
                      </span>

                      {/* Hot Slot Badge */}
                      {slotNumber !== null && (
                        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300">
                          <Star className="w-3 h-3 fill-current" />
                          Slot {slotNumber}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-500">
                      {model.size && <span>Size: {model.size}</span>}
                      {model.installed_at && (
                        <span>
                          Installed: {new Date(model.installed_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>

                    {!isInstalled && (
                      <p className="text-xs text-orange-600 dark:text-orange-400 mt-2">
                        ⚠️ Model not installed. Download it from Ollama to use it.
                      </p>
                    )}
                  </div>

                  {/* Visibility Toggle */}
                  <button
                    onClick={() => handleToggleVisibility(model.model_name)}
                    disabled={saving}
                    className={`p-2 rounded-lg transition-colors ${
                      isVisible
                        ? 'text-primary-600 dark:text-primary-400 hover:bg-primary-100 dark:hover:bg-primary-900/30'
                        : 'text-gray-400 dark:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                    title={isVisible ? 'Hide model' : 'Show model'}
                  >
                    {isVisible ? <Eye className="w-5 h-5" /> : <EyeOff className="w-5 h-5" />}
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>

      {/* Hot Slots */}
      <div className="pt-6 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2 mb-4">
          <Star className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Hot Slots
          </h3>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          Quick-access favorites for your most-used models (1-4)
        </p>

        <div className="space-y-3">
          {([1, 2, 3, 4] as const).map((slotNum) => {
            const assignedModel = hotSlots[slotNum]

            return (
              <div
                key={slotNum}
                className="p-4 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700"
              >
                <label className="block">
                  <div className="flex items-center gap-2 mb-2">
                    <Star
                      className={`w-4 h-4 ${
                        assignedModel
                          ? 'text-yellow-500 fill-yellow-500'
                          : 'text-gray-400 dark:text-gray-600'
                      }`}
                    />
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Hot Slot {slotNum}
                    </span>
                  </div>
                  <select
                    value={assignedModel || ''}
                    onChange={(e) => handleAssignSlot(slotNum, e.target.value || null)}
                    disabled={saving}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:opacity-50"
                  >
                    <option value="">-- Not assigned --</option>
                    {visibleModels.map((pref) => (
                      <option key={pref.model_name} value={pref.model_name}>
                        {pref.model_name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            )
          })}
        </div>

        {visibleModels.length === 0 && (
          <div className="mt-4 p-4 rounded-lg bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800">
            <p className="text-sm text-orange-800 dark:text-orange-200">
              ⚠️ No visible models available for hot slots. Make some models visible above first.
            </p>
          </div>
        )}
      </div>

      {/* Saving Indicator */}
      {saving && (
        <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
          <div className="flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-blue-600 dark:text-blue-400" />
            <span className="text-sm text-blue-900 dark:text-blue-100">
              Saving changes...
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
