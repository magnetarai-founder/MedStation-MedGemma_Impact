import { useState, useEffect } from 'react'
import { Package, CheckCircle, Info, Zap, Cpu, TrendingUp } from 'lucide-react'
import { SetupWizardState } from '../SetupWizard'
import { setupWizardApi } from '../../../lib/setupWizardApi'

interface StepProps {
  wizardState: SetupWizardState
  updateWizardState: (updates: Partial<SetupWizardState>) => void
  onNext: () => void
  onBack?: () => void
  onComplete?: () => void
}

interface ModelInfo {
  name: string
  display_name: string
  category: string
  size_gb: number
  description: string
  use_cases: string[]
  recommended_for: string
  performance: {
    speed: string
    quality: string
    context_window: number
  }
}

interface ModelRecommendations {
  tier: string
  models: ModelInfo[]
  hot_slot_recommendations: Record<number, string | null>
  total_size_gb: number
}

export default function ModelsStep(props: StepProps) {
  const [recommendations, setRecommendations] = useState<ModelRecommendations | null>(null)
  const [selectedModels, setSelectedModels] = useState<Set<string>>(new Set())
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadRecommendations()
  }, [])

  const loadRecommendations = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const data = await setupWizardApi.getModelRecommendations()
      setRecommendations(data)

      // Auto-select models based on hot slot recommendations
      const autoSelected = new Set<string>()
      Object.values(data.hot_slot_recommendations).forEach(modelName => {
        if (modelName) autoSelected.add(modelName)
      })
      setSelectedModels(autoSelected)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load model recommendations')
    } finally {
      setIsLoading(false)
    }
  }

  const toggleModel = (modelName: string) => {
    const newSelection = new Set(selectedModels)
    if (newSelection.has(modelName)) {
      newSelection.delete(modelName)
    } else {
      newSelection.add(modelName)
    }
    setSelectedModels(newSelection)
  }

  const handleNext = () => {
    // Store selected models in wizard state
    props.updateWizardState({
      selectedModels: Array.from(selectedModels)
    })
    props.onNext()
  }

  const getTierIcon = () => {
    switch (recommendations?.tier) {
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
    switch (recommendations?.tier) {
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
    switch (recommendations?.tier) {
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

  const selectedSize = recommendations?.models
    .filter(m => selectedModels.has(m.name))
    .reduce((sum, m) => sum + m.size_gb, 0) || 0

  return (
    <div className="max-w-4xl mx-auto p-8">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 dark:bg-primary-900/30 rounded-full mb-4">
          <Package className="w-8 h-8 text-primary-600 dark:text-primary-400" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          Select AI Models
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          Choose models to download based on your system resources
        </p>
      </div>

      {isLoading && (
        <div className="text-center py-12">
          <div className="inline-block w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading recommendations...</p>
        </div>
      )}

      {error && (
        <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {!isLoading && recommendations && (
        <div className="space-y-6">
          {/* Tier Info */}
          <div className={`p-4 bg-${getTierColor()}-50 dark:bg-${getTierColor()}-900/20 border border-${getTierColor()}-200 dark:border-${getTierColor()}-800 rounded-lg`}>
            <div className="flex items-center gap-3 mb-2">
              {getTierIcon()}
              <h3 className={`text-lg font-medium text-${getTierColor()}-900 dark:text-${getTierColor()}-100`}>
                {getTierName()}
              </h3>
            </div>
            <p className={`text-sm text-${getTierColor()}-800 dark:text-${getTierColor()}-200`}>
              We've pre-selected recommended models for your system. You can customize this selection below.
            </p>
          </div>

          {/* Selection Summary */}
          <div className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Selected Models</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {selectedModels.size} of {recommendations.models.length}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Total Download Size</p>
              <p className="text-2xl font-bold text-primary-600 dark:text-primary-400">
                {selectedSize.toFixed(1)} GB
              </p>
            </div>
          </div>

          {/* Model List */}
          <div className="space-y-3">
            {recommendations.models.map((model) => (
              <div
                key={model.name}
                className={`p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                  selectedModels.has(model.name)
                    ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                }`}
                onClick={() => toggleModel(model.name)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3 flex-1">
                    <div className="mt-1">
                      {selectedModels.has(model.name) ? (
                        <CheckCircle className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                      ) : (
                        <div className="w-5 h-5 border-2 border-gray-300 dark:border-gray-600 rounded-full" />
                      )}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-medium text-gray-900 dark:text-gray-100">
                          {model.display_name}
                        </h4>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
                          {model.category}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                        {model.description}
                      </p>
                      <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-500">
                        <span>Size: {model.size_gb} GB</span>
                        <span>Speed: {model.performance.speed}</span>
                        <span>Quality: {model.performance.quality}</span>
                      </div>
                      {Object.entries(recommendations.hot_slot_recommendations).some(
                        ([_, name]) => name === model.name
                      ) && (
                        <div className="mt-2 inline-flex items-center gap-1 text-xs text-primary-600 dark:text-primary-400">
                          <Info className="w-3 h-3" />
                          Recommended for hot slot
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 mt-8">
            {props.onBack && (
              <button
                onClick={props.onBack}
                className="flex-1 px-6 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                Back
              </button>
            )}
            <button
              onClick={handleNext}
              className="flex-1 px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 flex items-center justify-center gap-2"
            >
              {selectedModels.size > 0 ? (
                <>
                  Continue with {selectedModels.size} model{selectedModels.size > 1 ? 's' : ''}
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
