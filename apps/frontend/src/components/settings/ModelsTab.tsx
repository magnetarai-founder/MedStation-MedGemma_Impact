import { useState, useEffect } from 'react'
import { Cpu, Zap, Lock, Check, AlertTriangle } from 'lucide-react'

interface AgentModelSettings {
  orchestrator: {
    enabled: boolean
    model: string
  }
  user_preferences: {
    large_refactor: string
    multi_file: string
    code_generation: string
    deep_reasoning: string
    surgical: string
    chat_default: string
  }
  recommended_models: {
    [key: string]: string
  }
  strict_models: {
    data_engine: string
  }
  available_models: string[]
  note: string
}

export default function ModelsTab() {
  const [modelSettings, setModelSettings] = useState<AgentModelSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Task labels for display
  const taskLabels: { [key: string]: { label: string; description: string } } = {
    large_refactor: {
      label: 'Large Refactoring',
      description: 'Multi-file architectural changes and major rewrites'
    },
    multi_file: {
      label: 'Multi-File Operations',
      description: 'Cross-file edits, imports, and renames'
    },
    code_generation: {
      label: 'Code Generation',
      description: 'New features, boilerplate, and scaffolding'
    },
    deep_reasoning: {
      label: 'Deep Reasoning',
      description: 'Complex logic, algorithm design, and planning'
    },
    surgical: {
      label: 'Surgical Fixes',
      description: 'Precise single-file edits and bug fixes'
    },
    chat_default: {
      label: 'AI Chat Default',
      description: 'Default model for conversational AI in chat tab'
    }
  }

  // Load model settings from API
  useEffect(() => {
    const loadModelSettings = async () => {
      try {
        setLoading(true)
        const token = localStorage.getItem('auth_token')
        const response = await fetch('/api/v1/agent/models', {
          headers: {
            'Authorization': token ? `Bearer ${token}` : '',
            'Content-Type': 'application/json'
          }
        })

        if (!response.ok) {
          throw new Error('Failed to load model settings')
        }

        const data = await response.json()
        setModelSettings(data)
      } catch (err) {
        console.error('Failed to load model settings:', err)
        setError(err instanceof Error ? err.message : 'Failed to load settings')
      } finally {
        setLoading(false)
      }
    }

    loadModelSettings()
  }, [])

  // Toggle orchestrator
  const handleToggleOrchestrator = async (enabled: boolean) => {
    if (!modelSettings) return

    try {
      setSaving(true)
      const token = localStorage.getItem('auth_token')
      const response = await fetch('/api/v1/agent/models/update', {
        method: 'POST',
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          orchestrator: { enabled }
        })
      })

      if (!response.ok) {
        throw new Error('Failed to update orchestrator setting')
      }

      const data = await response.json()
      setModelSettings({
        ...modelSettings,
        orchestrator: data.orchestrator
      })
    } catch (err) {
      console.error('Failed to toggle orchestrator:', err)
      setError(err instanceof Error ? err.message : 'Failed to update')
    } finally {
      setSaving(false)
    }
  }

  // Update user preference for a task
  const handleUpdatePreference = async (task: string, model: string) => {
    if (!modelSettings) return

    try {
      setSaving(true)
      const token = localStorage.getItem('auth_token')
      const response = await fetch('/api/v1/agent/models/update', {
        method: 'POST',
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_preferences: { [task]: model }
        })
      })

      if (!response.ok) {
        throw new Error('Failed to update model preference')
      }

      const data = await response.json()
      setModelSettings({
        ...modelSettings,
        user_preferences: data.user_preferences
      })
    } catch (err) {
      console.error('Failed to update preference:', err)
      setError(err instanceof Error ? err.message : 'Failed to update')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex items-center gap-3 text-gray-500 dark:text-gray-400">
          <div className="w-5 h-5 border-2 border-gray-300 border-t-primary-600 rounded-full animate-spin"></div>
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
            Error Loading Settings
          </h4>
        </div>
        <p className="text-xs text-red-800 dark:text-red-200 mt-1">
          {error}
        </p>
      </div>
    )
  }

  if (!modelSettings) return null

  return (
    <div className="space-y-6">
      {/* Orchestrator Toggle */}
      <div>
        <div className="flex items-center space-x-2 mb-4">
          <Zap className="w-5 h-5 text-amber-600 dark:text-amber-400" />
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Orchestrator
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Intelligent model routing and task detection
            </p>
          </div>
        </div>

        <div className="space-y-4">
          {/* Toggle */}
          <div className="flex items-center justify-between p-4 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
            <div>
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  Enable Intelligent Routing
                </label>
                {modelSettings.orchestrator.enabled && (
                  <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300">
                    <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></div>
                    <span className="text-xs font-medium">Active</span>
                  </div>
                )}
              </div>
              <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                Auto-select the best model for each task using {modelSettings.orchestrator.model}
              </p>
            </div>
            <button
              onClick={() => handleToggleOrchestrator(!modelSettings.orchestrator.enabled)}
              disabled={saving}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                modelSettings.orchestrator.enabled
                  ? 'bg-primary-600'
                  : 'bg-gray-300 dark:bg-gray-600'
              } ${saving ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  modelSettings.orchestrator.enabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* Info card */}
          <div className="p-4 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
            <h4 className="text-sm font-semibold text-amber-900 dark:text-amber-100 mb-2">
              About Orchestrator
            </h4>
            <ul className="text-xs text-amber-800 dark:text-amber-200 space-y-1">
              <li>• Automatically selects the best model for each coding task</li>
              <li>• Uses {modelSettings.orchestrator.model} for lightweight routing decisions</li>
              <li>• When disabled, you manually select models for each task type below</li>
              <li>• Optimizes for speed vs quality based on task complexity</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Task-Specific Models (only shown when orchestrator is OFF) */}
      {!modelSettings.orchestrator.enabled && (
        <div>
          <div className="flex items-center space-x-2 mb-4">
            <Cpu className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Task-Specific Models
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Manually select models for each type of coding task
              </p>
            </div>
          </div>

          <div className="space-y-4">
            {Object.entries(modelSettings.user_preferences).map(([task, selectedModel]) => {
              const taskInfo = taskLabels[task]
              if (!taskInfo) return null

              return (
                <div key={task} className="p-4 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
                  <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">
                    {taskInfo.label}
                  </label>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-3">
                    {taskInfo.description}
                  </p>
                  <select
                    value={selectedModel}
                    onChange={(e) => handleUpdatePreference(task, e.target.value)}
                    disabled={saving}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 disabled:opacity-50"
                  >
                    {modelSettings.available_models.map((model) => {
                      const isRecommended = modelSettings.recommended_models[task] === model
                      return (
                        <option key={model} value={model}>
                          {model} {isRecommended ? '✓ Tested' : ''}
                        </option>
                      )
                    })}
                  </select>
                  {modelSettings.recommended_models[task] === selectedModel && (
                    <div className="flex items-center gap-1 mt-2 text-xs text-green-600 dark:text-green-400">
                      <Check className="w-3 h-3" />
                      <span>Recommended and tested by ElohimOS</span>
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Note about non-recommended models */}
          <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
            <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-2">
              Model Selection
            </h4>
            <ul className="text-xs text-blue-800 dark:text-blue-200 space-y-1">
              <li>• ✓ Tested models are verified to work well with ElohimOS</li>
              <li>• Other models may work but could have unexpected behavior</li>
              <li>• Aider and Continue will naturally reject unsupported models</li>
              <li>• Changes save automatically</li>
            </ul>
          </div>
        </div>
      )}

      {/* Data Engine (always shown, always locked) */}
      <div>
        <div className="flex items-center space-x-2 mb-4">
          <Lock className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Data Engine
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Dedicated model for database operations
            </p>
          </div>
        </div>

        <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-gray-900 dark:text-gray-100">
              Model
            </label>
            <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
              <Lock className="w-3 h-3" />
              <span className="text-xs font-medium">Locked</span>
            </div>
          </div>
          <input
            type="text"
            value={modelSettings.strict_models.data_engine}
            disabled
            className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-gray-100 dark:bg-gray-900 text-gray-500 dark:text-gray-400 cursor-not-allowed"
          />
          <p className="text-xs text-gray-600 dark:text-gray-400 mt-2">
            This model is locked to phi3.5 for reliable schema discovery and SQL generation. It cannot be changed.
          </p>
        </div>
      </div>

      {/* Current Status Summary */}
      {saving && (
        <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin"></div>
            <span className="text-sm text-blue-900 dark:text-blue-100">
              Saving changes...
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
