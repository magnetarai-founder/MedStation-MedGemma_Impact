import { useState, useEffect } from 'react'
import { useChatStore } from '@/stores/chatStore'

export default function ChatTab() {
  const {
    settings,
    availableModels,
    setAvailableModels,
    updateSettings,
    updateModelConfig,
    getModelConfig
  } = useChatStore()

  // Currently selected model for configuration ("" = None/Global)
  const [selectedConfigModel, setSelectedConfigModel] = useState<string>('')

  // Load models on mount
  useEffect(() => {
    const loadModels = async () => {
      try {
        const response = await fetch(`/api/v1/chat/models/status`)
        if (response.ok) {
          const data = await response.json()
          // Show ALL models (both available and unavailable) for configuration
          // Users should be able to configure settings for any model they have
          const allModels = [
            ...(data.available || []),
            ...(data.unavailable || [])
          ]
          setAvailableModels(allModels)
        }
      } catch (error) {
        console.error('Failed to load models:', error)
      }
    }
    loadModels()
  }, [setAvailableModels])

  // Get configuration for selected model or global settings
  const isGlobalSettings = selectedConfigModel === ''
  const modelConfig = isGlobalSettings ? null : getModelConfig(selectedConfigModel)

  // Active config values (either global or per-model)
  const activeConfig = isGlobalSettings
    ? {
        tone: settings.tone,
        temperature: settings.temperature ?? 0.7,
        topP: settings.topP ?? 0.9,
        topK: settings.topK ?? 40,
        repeatPenalty: settings.repeatPenalty ?? 1.1,
        systemPrompt: settings.systemPrompt || ''
      }
    : {
        tone: modelConfig?.tone || 'balanced',
        temperature: modelConfig?.temperature ?? 0.7,
        topP: modelConfig?.topP ?? 0.9,
        topK: modelConfig?.topK ?? 40,
        repeatPenalty: modelConfig?.repeatPenalty ?? 1.1,
        systemPrompt: modelConfig?.systemPrompt || ''
      }

  // Update handler
  const handleUpdate = (updates: any) => {
    if (isGlobalSettings) {
      updateSettings(updates)
    } else {
      updateModelConfig(selectedConfigModel, updates)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          AI Chat Parameters
        </h3>

        <div className="space-y-4">
          {/* Model Settings Selector */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Model Settings
            </label>
            <select
              value={selectedConfigModel}
              onChange={(e) => setSelectedConfigModel(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            >
              <option value="">None (Global Settings)</option>
              {availableModels.length === 0 ? (
                <option value="" disabled>Loading models...</option>
              ) : (
                availableModels.map((model) => (
                  <option key={model.name} value={model.name}>
                    {model.name}
                  </option>
                ))
              )}
            </select>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {isGlobalSettings
                ? 'Configure global app settings (like ChatGPT personalization)'
                : `Configure settings specifically for ${selectedConfigModel}`
              }
            </p>
          </div>

          {/* Tone Presets */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Tone Preset
            </label>
            <div className="grid grid-cols-2 gap-2">
              {(['creative', 'balanced', 'precise', 'custom'] as const).map((tone) => (
                <button
                  key={tone}
                  onClick={() => handleUpdate({ tone })}
                  className={`px-3 py-2 text-xs font-medium rounded-lg border transition-all ${
                    activeConfig.tone === tone
                      ? 'bg-primary-100 dark:bg-primary-900/30 border-primary-500 text-primary-700 dark:text-primary-300'
                      : 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:border-primary-300'
                  }`}
                >
                  {tone.charAt(0).toUpperCase() + tone.slice(1)}
                </button>
              ))}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {activeConfig.tone === 'creative' && 'Higher temp, more creative & varied'}
              {activeConfig.tone === 'balanced' && 'Balanced creativity & accuracy'}
              {activeConfig.tone === 'precise' && 'Lower temp, more focused & deterministic'}
              {activeConfig.tone === 'custom' && 'Use custom parameters below'}
            </p>
          </div>

          {/* Temperature */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Temperature
              </label>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {activeConfig.temperature.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="2"
              step="0.05"
              value={activeConfig.temperature}
              onChange={(e) => handleUpdate({ temperature: parseFloat(e.target.value), tone: 'custom' })}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
              disabled={activeConfig.tone !== 'custom'}
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Controls randomness (0 = deterministic, 2 = very creative)</p>
          </div>

          {/* Top P */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Top P (Nucleus Sampling)
              </label>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {activeConfig.topP.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={activeConfig.topP}
              onChange={(e) => handleUpdate({ topP: parseFloat(e.target.value), tone: 'custom' })}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
              disabled={activeConfig.tone !== 'custom'}
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Cumulative probability cutoff for token selection</p>
          </div>

          {/* Top K */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Top K
              </label>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {activeConfig.topK}
              </span>
            </div>
            <input
              type="range"
              min="1"
              max="100"
              step="1"
              value={activeConfig.topK}
              onChange={(e) => handleUpdate({ topK: parseInt(e.target.value), tone: 'custom' })}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
              disabled={activeConfig.tone !== 'custom'}
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Limits sampling to top K most likely tokens</p>
          </div>

          {/* Repeat Penalty */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Repeat Penalty
              </label>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {activeConfig.repeatPenalty.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="2"
              step="0.05"
              value={activeConfig.repeatPenalty}
              onChange={(e) => handleUpdate({ repeatPenalty: parseFloat(e.target.value), tone: 'custom' })}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
              disabled={activeConfig.tone !== 'custom'}
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Penalizes repetition (1.0 = no penalty, higher = less repetition)</p>
          </div>

          {/* System Prompt */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {isGlobalSettings ? 'Global System Prompt' : 'Model-Specific System Prompt'}
            </label>
            <textarea
              value={activeConfig.systemPrompt}
              onChange={(e) => handleUpdate({ systemPrompt: e.target.value })}
              placeholder={
                isGlobalSettings
                  ? 'You are a helpful AI assistant... (applies to all models unless overridden)'
                  : `Override global system prompt for ${selectedConfigModel}...`
              }
              rows={3}
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 resize-none"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {isGlobalSettings
                ? 'Instructions sent with every message (all models)'
                : 'Overrides global system prompt when using this model'
              }
            </p>
          </div>

          {/* Global Settings Only */}
          {isGlobalSettings && (
            <>
              {/* Auto-generate titles */}
              <div className="flex items-center justify-between">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Auto-generate titles</label>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Name chats from first message</p>
                </div>
                <input
                  type="checkbox"
                  checked={settings.autoGenerateTitles}
                  onChange={(e) => updateSettings({ autoGenerateTitles: e.target.checked })}
                  className="w-4 h-4 rounded text-primary-600"
                />
              </div>

              {/* Context Window (locked) */}
              <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100">Context Window: 200k tokens</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Last 75 messages sent in full, earlier messages automatically summarized</p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
