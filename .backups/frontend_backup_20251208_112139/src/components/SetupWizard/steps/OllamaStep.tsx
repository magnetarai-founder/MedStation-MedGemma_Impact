import { useState, useEffect } from 'react'
import { Server, CheckCircle, XCircle, AlertCircle, ExternalLink, RefreshCw } from 'lucide-react'
import { SetupWizardState } from '../SetupWizard'
import { setupWizardApi } from '../../../lib/setupWizardApi'

interface StepProps {
  wizardState: SetupWizardState
  updateWizardState: (updates: Partial<SetupWizardState>) => void
  onNext: () => void
  onBack?: () => void
  onComplete?: () => void
}

interface OllamaStatus {
  installed: boolean
  running: boolean
  version: string | null
  base_url: string
  install_instructions: {
    method?: string
    command?: string
    url?: string
    service_start?: string
  }
}

export default function OllamaStep(props: StepProps) {
  const [status, setStatus] = useState<OllamaStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const checkOllama = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const result = await setupWizardApi.checkOllama()
      setStatus(result)

      // Update wizard state
      props.updateWizardState({
        ollamaInstalled: result.installed,
        ollamaRunning: result.running
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to check Ollama status')
    } finally {
      setIsLoading(false)
    }
  }

  // Check on mount
  useEffect(() => {
    checkOllama()
  }, [])

  const handleNext = () => {
    if (status?.installed && status?.running) {
      props.onNext()
    }
  }

  const canProceed = status?.installed && status?.running

  return (
    <div className="max-w-2xl mx-auto p-8">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 dark:bg-primary-900/30 rounded-full mb-4">
          <Server className="w-8 h-8 text-primary-600 dark:text-primary-400" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          Ollama Setup
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          Ollama is required to run local AI models on your machine.
        </p>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="text-center py-12">
          <div className="inline-block w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Checking Ollama status...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-800 dark:text-red-200">{error}</p>
              <button
                onClick={checkOllama}
                className="mt-2 text-sm text-red-600 dark:text-red-400 hover:underline"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Status Display */}
      {!isLoading && status && (
        <div className="space-y-6">
          {/* Installation Status */}
          <div className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-gray-900 dark:text-gray-100">Ollama Binary</span>
              {status.installed ? (
                <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                  <CheckCircle className="w-5 h-5" />
                  <span className="text-sm">Installed</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
                  <XCircle className="w-5 h-5" />
                  <span className="text-sm">Not Installed</span>
                </div>
              )}
            </div>
            {status.version && (
              <p className="text-sm text-gray-600 dark:text-gray-400">Version: {status.version}</p>
            )}
          </div>

          {/* Service Status */}
          <div className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-gray-900 dark:text-gray-100">Ollama Service</span>
              {status.running ? (
                <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                  <CheckCircle className="w-5 h-5" />
                  <span className="text-sm">Running</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-orange-600 dark:text-orange-400">
                  <XCircle className="w-5 h-5" />
                  <span className="text-sm">Not Running</span>
                </div>
              )}
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">URL: {status.base_url}</p>
          </div>

          {/* Installation Instructions (if needed) */}
          {(!status.installed || !status.running) && (
            <div className="p-6 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
              <h3 className="font-medium text-blue-900 dark:text-blue-100 mb-4">
                {!status.installed ? 'Install Ollama' : 'Start Ollama Service'}
              </h3>

              {!status.installed && status.install_instructions && (
                <div className="space-y-3">
                  <p className="text-sm text-blue-800 dark:text-blue-200">
                    Installation method: <strong>{status.install_instructions.method || 'manual'}</strong>
                  </p>

                  {status.install_instructions.command && (
                    <div>
                      <p className="text-sm text-blue-800 dark:text-blue-200 mb-2">Run this command:</p>
                      <div className="p-3 bg-blue-100 dark:bg-blue-900/40 rounded font-mono text-sm text-blue-900 dark:text-blue-100">
                        {status.install_instructions.command}
                      </div>
                    </div>
                  )}

                  {status.install_instructions.url && (
                    <a
                      href={status.install_instructions.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400 hover:underline"
                    >
                      <ExternalLink className="w-4 h-4" />
                      Download from {status.install_instructions.url}
                    </a>
                  )}
                </div>
              )}

              {status.installed && !status.running && status.install_instructions.service_start && (
                <div>
                  <p className="text-sm text-blue-800 dark:text-blue-200 mb-2">Start the service:</p>
                  <div className="p-3 bg-blue-100 dark:bg-blue-900/40 rounded font-mono text-sm text-blue-900 dark:text-blue-100">
                    {status.install_instructions.service_start}
                  </div>
                </div>
              )}

              <button
                onClick={checkOllama}
                className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                <RefreshCw className="w-4 h-4" />
                Check Again
              </button>
            </div>
          )}

          {/* Success Message */}
          {canProceed && (
            <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
              <div className="flex items-start gap-3">
                <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-green-800 dark:text-green-200">
                    Ollama is ready! You can proceed to model selection.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Action Buttons */}
      {!isLoading && (
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
            disabled={!canProceed}
            className="flex-1 px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {canProceed ? (
              <>
                <CheckCircle className="w-4 h-4" />
                Continue
              </>
            ) : (
              'Install Ollama to Continue'
            )}
          </button>
        </div>
      )}
    </div>
  )
}
