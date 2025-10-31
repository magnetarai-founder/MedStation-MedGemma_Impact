import { useState, useEffect } from 'react'
import { Cpu, Zap } from 'lucide-react'
import { type NavTab } from '@/stores/navigationStore'
import { useChatStore } from '@/stores/chatStore'

interface ModelsTabProps {
  activeNavTab?: NavTab
}

export default function ModelsTab({ activeNavTab }: ModelsTabProps = {}) {
  const { settings, availableModels, setAvailableModels, updateSettings } = useChatStore()

  const [localSettings, setLocalSettings] = useState({
    app_memory_percent: 30,
    processing_memory_percent: 40,
    cache_memory_percent: 20,
  })

  // Load available models on mount
  useEffect(() => {
    const loadModels = async () => {
      try {
        const response = await fetch(`/api/v1/chat/models/status`)
        if (response.ok) {
          const data = await response.json()
          // Only show available (chat) models
          setAvailableModels(data.available || [])
        }
      } catch (error) {
        console.error('Failed to load models:', error)
      }
    }
    loadModels()
  }, [setAvailableModels])

  // Load settings on mount
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const response = await fetch('/api/settings')
        if (response.ok) {
          const data = await response.json()
          setLocalSettings({
            app_memory_percent: data.app_memory_percent ?? 35,
            processing_memory_percent: data.processing_memory_percent ?? 50,
            cache_memory_percent: data.cache_memory_percent ?? 15,
          })
        }
      } catch (error) {
        console.error('Failed to load settings:', error)
      }
    }
    loadSettings()
  }, [])

  // Save settings
  const handleSaveSettings = async () => {
    try {
      // Fetch current settings first
      const getResponse = await fetch('/api/settings')
      if (!getResponse.ok) {
        throw new Error('Failed to fetch current settings')
      }
      const currentSettings = await getResponse.json()

      // Merge with local changes
      const updatedSettings = {
        ...currentSettings,
        ...localSettings
      }

      // Save merged settings
      const response = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedSettings),
      })

      if (!response.ok) {
        throw new Error('Failed to save settings')
      }
    } catch (error) {
      console.error('Failed to save settings:', error)
    }
  }

  // Auto-save on change
  useEffect(() => {
    const timer = setTimeout(() => {
      handleSaveSettings()
    }, 1000)
    return () => clearTimeout(timer)
  }, [localSettings])

  return (
    <div className="space-y-6">
      {/* Orchestrator Model */}
      <div>
        <div className="flex items-center space-x-2 mb-4">
          <Zap className="w-5 h-5 text-amber-600 dark:text-amber-400" />
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Orchestrator Model
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Always-running model that powers Jarvis intelligent routing
            </p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Orchestrator Model
            </label>
            <select
              value={settings.orchestratorModel}
              onChange={(e) => updateSettings({ orchestratorModel: e.target.value })}
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            >
              <option value="">None (Disable orchestrator)</option>
              {availableModels.length === 0 ? (
                <option value="" disabled>Loading models...</option>
              ) : (
                availableModels.map((model) => (
                  <option key={model.name} value={model.name}>
                    {model.name} ({model.size})
                  </option>
                ))
              )}
            </select>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Recommended: Small efficient models (1.5B-3B parameters) like llama3.2:1b or qwen2.5:0.5b
            </p>
          </div>

          {/* Info card */}
          <div className="p-4 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
            <h4 className="text-sm font-semibold text-amber-900 dark:text-amber-100 mb-2">
              About Orchestrator
            </h4>
            <ul className="text-xs text-amber-800 dark:text-amber-200 space-y-1">
              <li>• Always running in background for instant Jarvis responses</li>
              <li>• Powers intelligent model routing and task detection</li>
              <li>• Manages resource allocation (lazy loading/unloading models)</li>
              <li>• Cannot be unloaded while app is running</li>
              <li>• Choose a small, efficient model (1.5B-3B params recommended)</li>
            </ul>
          </div>

          {/* Current orchestrator status */}
          {settings.orchestratorModel && (
            <div className="p-4 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                <h4 className="text-sm font-semibold text-green-900 dark:text-green-100">
                  Orchestrator Active
                </h4>
              </div>
              <p className="text-xs text-green-800 dark:text-green-200 mt-1">
                Running: {settings.orchestratorModel}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Memory Allocation */}
      <div>
        <div className="flex items-center space-x-2 mb-4">
          <Cpu className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Memory Allocation
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Configure how system memory is allocated for model operations
            </p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              App memory: {localSettings.app_memory_percent}%
            </label>
            <input
              type="range"
              min="10"
              max="80"
              value={localSettings.app_memory_percent}
              onChange={(e) =>
                setLocalSettings({
                  ...localSettings,
                  app_memory_percent: parseInt(e.target.value),
                })
              }
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Percentage of system memory for app operations
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Processing memory: {localSettings.processing_memory_percent}%
            </label>
            <input
              type="range"
              min="10"
              max="80"
              value={localSettings.processing_memory_percent}
              onChange={(e) =>
                setLocalSettings({
                  ...localSettings,
                  processing_memory_percent: parseInt(e.target.value),
                })
              }
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Percentage of system memory for data processing
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Cache memory: {localSettings.cache_memory_percent}%
            </label>
            <input
              type="range"
              min="5"
              max="40"
              value={localSettings.cache_memory_percent}
              onChange={(e) =>
                setLocalSettings({
                  ...localSettings,
                  cache_memory_percent: parseInt(e.target.value),
                })
              }
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Percentage of system memory for caching
            </p>
          </div>

          {/* Info card */}
          <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
            <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-2">
              Memory Recommendations
            </h4>
            <ul className="text-xs text-blue-800 dark:text-blue-200 space-y-1">
              <li>• Total allocation should not exceed 100% of system memory</li>
              <li>• Processing memory affects model inference speed</li>
              <li>• Cache memory improves response times for repeated queries</li>
              <li>• Settings auto-save after changes</li>
            </ul>
          </div>

          {/* Current allocation summary */}
          <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
            <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Current Allocation
            </h4>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">App:</span>
                <span className="text-gray-900 dark:text-gray-100 font-medium">
                  {localSettings.app_memory_percent}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Processing:</span>
                <span className="text-gray-900 dark:text-gray-100 font-medium">
                  {localSettings.processing_memory_percent}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Cache:</span>
                <span className="text-gray-900 dark:text-gray-100 font-medium">
                  {localSettings.cache_memory_percent}%
                </span>
              </div>
              <div className="flex justify-between pt-2 mt-2 border-t border-gray-300 dark:border-gray-600">
                <span className="text-gray-700 dark:text-gray-300 font-medium">Total:</span>
                <span className={`font-bold ${
                  localSettings.app_memory_percent + localSettings.processing_memory_percent + localSettings.cache_memory_percent > 100
                    ? 'text-red-600 dark:text-red-400'
                    : 'text-green-600 dark:text-green-400'
                }`}>
                  {localSettings.app_memory_percent + localSettings.processing_memory_percent + localSettings.cache_memory_percent}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
