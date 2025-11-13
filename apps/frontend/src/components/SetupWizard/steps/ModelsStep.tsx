import { useState, useEffect } from 'react'
import { Package, CheckCircle, Eye, EyeOff, Zap, Cpu, TrendingUp } from 'lucide-react'
import { SetupWizardState } from '../SetupWizard'
import { userModelsApi, ModelCatalogItem, ModelPreferenceItem } from '../../../lib/userModelsApi'
import { setupWizardApi } from '../../../lib/setupWizardApi'

interface StepProps {
  wizardState: SetupWizardState
  updateWizardState: (updates: Partial<SetupWizardState>) => void
  onNext: () => void
  onBack?: () => void
  onComplete?: () => void
}

export default function ModelsStep(props: StepProps) {
  const [catalog, setCatalog] = useState<ModelCatalogItem[]>([])
  const [visibilityMap, setVisibilityMap] = useState<Map<string, boolean>>(new Map())
  const [tier, setTier] = useState<string>('balanced')
  const [ramGb, setRamGb] = useState<number>(16)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setIsLoading(true)
    setError(null)

    try {
      // Load system resources to determine tier
      const resources = await setupWizardApi.getSystemResources()
      setTier(resources.recommended_tier)
      setRamGb(resources.ram_gb)

      // Load global model catalog
      const catalogResponse = await userModelsApi.getModelCatalog()
      setCatalog(catalogResponse.models)

      // Try to load existing preferences
      try {
        const prefsResponse = await userModelsApi.getModelPreferences()
        const visMap = new Map<string, boolean>()

        if (prefsResponse.preferences.length > 0) {
          // User has existing preferences - load them
          prefsResponse.preferences.forEach(pref => {
            visMap.set(pref.model_name, pref.visible)
          })
        } else {
          // New user - initialize all installed models as visible by default
          catalogResponse.models.forEach(model => {
            visMap.set(model.model_name, true)
          })
        }

        setVisibilityMap(visMap)
      } catch (err) {
        // If preferences fail to load (e.g., not logged in yet), default all visible
        const visMap = new Map<string, boolean>()
        catalogResponse.models.forEach(model => {
          visMap.set(model.model_name, true)
        })
        setVisibilityMap(visMap)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load models')
    } finally {
      setIsLoading(false)
    }
  }

  const toggleVisibility = (modelName: string) => {
    setVisibilityMap(prev => {
      const newMap = new Map(prev)
      newMap.set(modelName, !prev.get(modelName))
      return newMap
    })
  }

  const handleNext = async () => {
    setIsLoading(true)
    setError(null)

    try {
      // Build preferences from visibility map
      const preferences: ModelPreferenceItem[] = Array.from(visibilityMap.entries()).map(
        ([model_name, visible], index) => ({
          model_name,
          visible,
          preferred: false,
          display_order: index + 1
        })
      )

      // Save preferences to backend
      await userModelsApi.updateModelPreferences(preferences)

      // Store visible models in wizard state (for hot slots step)
      const visibleModels = catalog
        .filter(m => visibilityMap.get(m.model_name))
        .map(m => m.model_name)

      props.updateWizardState({
        selectedModels: visibleModels
      })

      props.onNext()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save preferences')
      setIsLoading(false)
    }
  }

  const getTierIcon = () => {
    switch (tier) {
      case 'essential':
        return <Zap className="w-6 h-6 text-green-600 dark:text-green-400" />
      case 'balanced':
        return <Cpu className="w-6 h-6 text-blue-600 dark:text-blue-400" />
      case 'power_user':
        return <TrendingUp className="w-6 h-6 text-purple-600 dark:text-purple-400" />
      default:
        return <Package className="w-6 h-6" />
    }
  }

  const getTierColor = () => {
    switch (tier) {
      case 'essential':
        return 'green'
      case 'balanced':
        return 'blue'
      case 'power_user':
        return 'purple'
      default:
        return 'gray'
    }
  }

  const getTierName = () => {
    switch (tier) {
      case 'essential':
        return 'Essential (8GB+ RAM)'
      case 'balanced':
        return 'Balanced (16GB+ RAM)'
      case 'power_user':
        return 'Power User (32GB+ RAM)'
      default:
        return 'Unknown'
    }
  }

  const visibleCount = Array.from(visibilityMap.values()).filter(v => v).length

  return (
    <div className="max-w-4xl mx-auto p-8">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 dark:bg-primary-900/30 rounded-full mb-4">
          <Package className="w-8 h-8 text-primary-600 dark:text-primary-400" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          Choose Your Models
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          Select which AI models you want to see and use
        </p>
      </div>

      {isLoading && (
        <div className="text-center py-12">
          <div className="inline-block w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading models...</p>
        </div>
      )}

      {error && (
        <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {!isLoading && catalog.length === 0 && (
        <div className="text-center py-12">
          <Package className="w-16 h-16 text-gray-400 dark:text-gray-600 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            No models found. Make sure Ollama is running and has models installed.
          </p>
          <button
            onClick={props.onNext}
            className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            Skip Model Selection
          </button>
        </div>
      )}

      {!isLoading && catalog.length > 0 && (
        <div className="space-y-6">
          {/* Tier Info */}
          <div className={`p-4 bg-${getTierColor()}-50 dark:bg-${getTierColor()}-900/20 border border-${getTierColor()}-200 dark:border-${getTierColor()}-800 rounded-lg`}>
            <div className="flex items-center gap-3 mb-2">
              {getTierIcon()}
              <h3 className={`text-lg font-medium text-${getTierColor()}-900 dark:text-${getTierColor()}-100`}>
                {getTierName()} Detected
              </h3>
            </div>
            <p className={`text-sm text-${getTierColor()}-800 dark:text-${getTierColor()}-200`}>
              Your system has {ramGb}GB RAM. Choose which models you want visible in your model selector.
              You can change this anytime in Settings.
            </p>
          </div>

          {/* Selection Summary */}
          <div className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Visible Models</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {visibleCount} of {catalog.length}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Installed Models</p>
              <p className="text-2xl font-bold text-primary-600 dark:text-primary-400">
                {catalog.length}
              </p>
            </div>
          </div>

          {/* Info Banner */}
          <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <p className="text-sm text-blue-800 dark:text-blue-200">
              💡 <strong>Personal Preferences:</strong> These visibility settings are personal to you.
              Other users on this device can have different preferences.
            </p>
          </div>

          {/* Model List */}
          <div className="space-y-3">
            {catalog.map((model) => {
              const isVisible = visibilityMap.get(model.model_name) ?? true

              return (
                <div
                  key={model.model_name}
                  className={`p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                    isVisible
                      ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                      : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                  }`}
                  onClick={() => toggleVisibility(model.model_name)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3 flex-1">
                      <div className="mt-1">
                        {isVisible ? (
                          <Eye className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                        ) : (
                          <EyeOff className="w-5 h-5 text-gray-400 dark:text-gray-600" />
                        )}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="font-medium text-gray-900 dark:text-gray-100">
                            {model.model_name}
                          </h4>
                          <span className={`text-xs px-2 py-0.5 rounded-full ${
                            model.status === 'installed'
                              ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                              : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                          }`}>
                            {model.status}
                          </span>
                        </div>
                        <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-500">
                          {model.size && <span>Size: {model.size}</span>}
                          {model.installed_at && (
                            <span>
                              Installed: {new Date(model.installed_at).toLocaleDateString()}
                            </span>
                          )}
                        </div>
                        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                          {isVisible ? 'Visible in model selector' : 'Hidden from model selector'}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 mt-8">
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
              ) : visibleCount > 0 ? (
                <>
                  <CheckCircle className="w-4 h-4" />
                  Continue with {visibleCount} model{visibleCount > 1 ? 's' : ''}
                </>
              ) : (
                'Skip Model Selection'
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
