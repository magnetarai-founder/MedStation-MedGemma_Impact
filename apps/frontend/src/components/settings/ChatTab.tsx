import { useState, useEffect } from 'react'
import { useChatStore } from '@/stores/chatStore'

export default function ChatTab() {
  const {
    settings,
    availableModels,
    setAvailableModels,
    updateSettings
  } = useChatStore()

  // Ensure settings have all required fields with defaults
  const safeSettings = {
    tone: settings.tone || 'balanced',
    temperature: settings.temperature ?? 0.7,
    topP: settings.topP ?? 0.9,
    topK: settings.topK ?? 40,
    repeatPenalty: settings.repeatPenalty ?? 1.1,
    systemPrompt: settings.systemPrompt || '',
    ...settings
  }

  // Load models on mount
  useEffect(() => {
    const loadModels = async () => {
      try {
        const response = await fetch(`/api/v1/chat/models`)
        if (response.ok) {
          const models = await response.json()
          setAvailableModels(models)
        }
      } catch (error) {
        console.error('Failed to load models:', error)
      }
    }
    loadModels()
  }, [setAvailableModels])

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          AI Chat Parameters
        </h3>

        <div className="space-y-4">
          {/* Model Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Default Model
            </label>
            <select
              value={settings.defaultModel}
              onChange={(e) => updateSettings({ defaultModel: e.target.value })}
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            >
              {availableModels.length === 0 ? (
                <option value="">Loading models...</option>
              ) : (
                availableModels.map((model) => (
                  <option key={model.name} value={model.name}>
                    {model.name} ({model.size})
                  </option>
                ))
              )}
            </select>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Pre-loaded on app start</p>
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
                  onClick={() => updateSettings({ tone })}
                  className={`px-3 py-2 text-xs font-medium rounded-lg border transition-all ${
                    safeSettings.tone === tone
                      ? 'bg-primary-100 dark:bg-primary-900/30 border-primary-500 text-primary-700 dark:text-primary-300'
                      : 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:border-primary-300'
                  }`}
                >
                  {tone.charAt(0).toUpperCase() + tone.slice(1)}
                </button>
              ))}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {safeSettings.tone === 'creative' && 'Higher temp, more creative & varied'}
              {safeSettings.tone === 'balanced' && 'Balanced creativity & accuracy'}
              {safeSettings.tone === 'precise' && 'Lower temp, more focused & deterministic'}
              {safeSettings.tone === 'custom' && 'Use custom parameters below'}
            </p>
          </div>

          {/* Temperature */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Temperature
              </label>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {safeSettings.temperature.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="2"
              step="0.05"
              value={safeSettings.temperature}
              onChange={(e) => updateSettings({ temperature: parseFloat(e.target.value), tone: 'custom' })}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
              disabled={safeSettings.tone !== 'custom'}
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
                {safeSettings.topP.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={safeSettings.topP}
              onChange={(e) => updateSettings({ topP: parseFloat(e.target.value), tone: 'custom' })}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
              disabled={safeSettings.tone !== 'custom'}
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
                {safeSettings.topK}
              </span>
            </div>
            <input
              type="range"
              min="1"
              max="100"
              step="1"
              value={safeSettings.topK}
              onChange={(e) => updateSettings({ topK: parseInt(e.target.value), tone: 'custom' })}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
              disabled={safeSettings.tone !== 'custom'}
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
                {safeSettings.repeatPenalty.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="2"
              step="0.05"
              value={safeSettings.repeatPenalty}
              onChange={(e) => updateSettings({ repeatPenalty: parseFloat(e.target.value), tone: 'custom' })}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
              disabled={safeSettings.tone !== 'custom'}
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Penalizes repetition (1.0 = no penalty, higher = less repetition)</p>
          </div>

          {/* System Prompt */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              System Prompt
            </label>
            <textarea
              value={safeSettings.systemPrompt}
              onChange={(e) => updateSettings({ systemPrompt: e.target.value })}
              placeholder="You are a helpful AI assistant..."
              rows={3}
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 resize-none"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Instructions sent with every message</p>
          </div>

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
        </div>
      </div>
    </div>
  )
}
