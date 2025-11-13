import { useState, useEffect } from 'react'
import { Download, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { SetupWizardState } from '../SetupWizard'

interface StepProps {
  wizardState: SetupWizardState
  updateWizardState: (updates: Partial<SetupWizardState>) => void
  onNext: () => void
  onBack?: () => void
  onComplete?: () => void
}

interface ModelDownloadProgress {
  model: string
  status: 'pending' | 'downloading' | 'complete' | 'error'
  progress: number
  message?: string
}

export default function DownloadStep(props: StepProps) {
  const [modelProgress, setModelProgress] = useState<Map<string, ModelDownloadProgress>>(new Map())
  const [isDownloading, setIsDownloading] = useState(false)
  const [currentModel, setCurrentModel] = useState<string | null>(null)
  const [allComplete, setAllComplete] = useState(false)

  const selectedModels = props.wizardState.selectedModels || []

  useEffect(() => {
    // Initialize progress tracking
    const initialProgress = new Map<string, ModelDownloadProgress>()
    selectedModels.forEach(model => {
      initialProgress.set(model, {
        model,
        status: 'pending',
        progress: 0
      })
    })
    setModelProgress(initialProgress)

    // Auto-start downloads if models were selected
    if (selectedModels.length > 0) {
      startDownloads()
    } else {
      setAllComplete(true)
    }
  }, [])

  const startDownloads = async () => {
    setIsDownloading(true)

    for (const modelName of selectedModels) {
      setCurrentModel(modelName)

      // Update status to downloading
      setModelProgress(prev => {
        const next = new Map(prev)
        next.set(modelName, { ...prev.get(modelName)!, status: 'downloading', progress: 0 })
        return next
      })

      try {
        // Use SSE endpoint for real-time progress
        const eventSource = new EventSource(
          `/api/v1/setup/models/download/progress?model_name=${encodeURIComponent(modelName)}`
        )

        await new Promise<void>((resolve, reject) => {
          eventSource.onmessage = (event) => {
            if (event.data === '[DONE]') {
              eventSource.close()
              resolve()
              return
            }

            try {
              const data = JSON.parse(event.data)

              setModelProgress(prev => {
                const next = new Map(prev)
                next.set(modelName, {
                  model: modelName,
                  status: data.status === 'complete' ? 'complete' : 'downloading',
                  progress: data.progress || 0,
                  message: data.message
                })
                return next
              })

              if (data.status === 'complete') {
                eventSource.close()
                resolve()
              } else if (data.status === 'error') {
                eventSource.close()
                reject(new Error(data.message || 'Download failed'))
              }
            } catch (err) {
              // Skip invalid JSON
            }
          }

          eventSource.onerror = () => {
            eventSource.close()
            reject(new Error('Connection error'))
          }
        })

        // Mark as complete
        setModelProgress(prev => {
          const next = new Map(prev)
          next.set(modelName, { model: modelName, status: 'complete', progress: 100 })
          return next
        })
      } catch (err) {
        // Mark as error
        setModelProgress(prev => {
          const next = new Map(prev)
          next.set(modelName, {
            model: modelName,
            status: 'error',
            progress: 0,
            message: err instanceof Error ? err.message : 'Download failed'
          })
          return next
        })
      }
    }

    setIsDownloading(false)
    setAllComplete(true)
  }

  const handleNext = () => {
    props.onNext()
  }

  const getStatusIcon = (status: ModelDownloadProgress['status']) => {
    switch (status) {
      case 'complete':
        return <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
      case 'downloading':
        return <Loader2 className="w-5 h-5 text-primary-600 dark:text-primary-400 animate-spin" />
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
      default:
        return <div className="w-5 h-5 border-2 border-gray-300 dark:border-gray-600 rounded-full" />
    }
  }

  const completedCount = Array.from(modelProgress.values()).filter(p => p.status === 'complete').length
  const errorCount = Array.from(modelProgress.values()).filter(p => p.status === 'error').length

  return (
    <div className="max-w-2xl mx-auto p-8">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 dark:bg-primary-900/30 rounded-full mb-4">
          <Download className="w-8 h-8 text-primary-600 dark:text-primary-400" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          Downloading Models
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          {isDownloading
            ? 'Please wait while we download your selected models...'
            : allComplete
            ? 'Downloads complete!'
            : 'No models selected to download'}
        </p>
      </div>

      {/* Progress Summary */}
      {selectedModels.length > 0 && (
        <div className="mb-6 p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600 dark:text-gray-400">Progress</span>
            <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
              {completedCount} of {selectedModels.length} complete
            </span>
          </div>
          <div className="mt-2 w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div
              className="bg-primary-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${(completedCount / selectedModels.length) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Model List */}
      <div className="space-y-3 mb-8">
        {Array.from(modelProgress.values()).map((progress) => (
          <div
            key={progress.model}
            className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg"
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-3">
                {getStatusIcon(progress.status)}
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {progress.model}
                </span>
              </div>
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {progress.progress.toFixed(0)}%
              </span>
            </div>
            {progress.status === 'downloading' && (
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                <div
                  className="bg-primary-600 h-1.5 rounded-full transition-all duration-300"
                  style={{ width: `${progress.progress}%` }}
                />
              </div>
            )}
            {progress.message && progress.status === 'error' && (
              <p className="mt-2 text-sm text-red-600 dark:text-red-400">{progress.message}</p>
            )}
          </div>
        ))}
      </div>

      {/* Error Summary */}
      {errorCount > 0 && (
        <div className="mb-6 p-4 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-orange-600 dark:text-orange-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-orange-800 dark:text-orange-200">
                {errorCount} model{errorCount > 1 ? 's' : ''} failed to download
              </p>
              <p className="text-xs text-orange-700 dark:text-orange-300 mt-1">
                You can download them manually later using the Ollama CLI
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3">
        {props.onBack && (
          <button
            onClick={props.onBack}
            disabled={isDownloading}
            className="flex-1 px-6 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Back
          </button>
        )}
        <button
          onClick={handleNext}
          disabled={isDownloading}
          className="flex-1 px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {isDownloading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Downloading...
            </>
          ) : (
            <>
              <CheckCircle className="w-4 h-4" />
              Continue
            </>
          )}
        </button>
      </div>
    </div>
  )
}
