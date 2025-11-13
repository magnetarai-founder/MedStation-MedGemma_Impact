import { useState, useEffect } from 'react'
import { Star, Loader2, CheckCircle2, Circle, Download } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useChatStore } from '@/stores/chatStore'

function ModelManagerSection() {
  const [favorites, setFavorites] = useState<string[]>([])

  // Query for model status
  const { data: modelStatus, isLoading, refetch } = useQuery({
    queryKey: ['model-status'],
    queryFn: async () => {
      const response = await fetch('/api/v1/chat/models/status')
      if (!response.ok) throw new Error('Failed to load model status')
      return await response.json()
    },
    refetchInterval: 5000 // Refresh every 5 seconds
  })

  // DEPRECATED: Favorites endpoint removed in favor of hot slots
  // Hot slots are managed via ModelManagementSidebar using:
  // - POST /api/v1/chat/models/hot-slots/{slot}
  // - DELETE /api/v1/chat/models/hot-slots/{slot}
  //
  // Load favorites (DISABLED - endpoint doesn't exist)
  useEffect(() => {
    // const loadFavorites = async () => {
    //   try {
    //     const response = await fetch('/api/v1/chat/models/favorites')
    //     if (response.ok) {
    //       const data = await response.json()
    //       setFavorites(data.favorites || [])
    //     }
    //   } catch (error) {
    //     console.error('Failed to load favorites:', error)
    //   }
    // }
    // loadFavorites()
  }, [])

  const toggleFavorite = async (modelName: string) => {
    // DISABLED - Use hot slots instead via ModelManagementSidebar
    console.warn('toggleFavorite is deprecated - use hot slots instead')
    // const isFavorite = favorites.includes(modelName)
    // try {
    //   const method = isFavorite ? 'DELETE' : 'POST'
    //   const response = await fetch(`/api/v1/chat/models/favorites/${encodeURIComponent(modelName)}`, { method })
    //
    //   if (response.ok) {
    //     const data = await response.json()
    //     setFavorites(data.favorites || [])
    //   }
    // } catch (error) {
    //   console.error('Failed to toggle favorite:', error)
    // }
  }

  const preloadModel = async (modelName: string) => {
    try {
      await fetch(`/api/v1/chat/models/preload?model=${encodeURIComponent(modelName)}&keep_alive=1h`, { method: 'POST' })
      await refetch()
    } catch (error) {
      console.error('Failed to preload model:', error)
    }
  }

  const unloadModel = async (modelName: string) => {
    try {
      await fetch(`/api/v1/chat/models/unload/${encodeURIComponent(modelName)}`, { method: 'POST' })
      await refetch()
    } catch (error) {
      console.error('Failed to unload model:', error)
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Model Manager
          </h3>
          <div className="text-center py-8 text-gray-500">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
            <p>Loading models...</p>
          </div>
        </div>
      </div>
    )
  }

  // Only show available (chat) models in settings
  const models = modelStatus?.available || []

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Model Manager
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          Manage installed Ollama models. Favorites are auto-loaded on startup for instant responses.
        </p>

        {models.length === 0 ? (
          <div className="p-6 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-center">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
              No models installed yet
            </p>
            <a
              href="https://ollama.com/library"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm"
            >
              <Download className="w-4 h-4" />
              <span>Browse Ollama Library</span>
            </a>
          </div>
        ) : (
          <div className="space-y-2">
            {models.map((model: any) => {
              const isFavorite = favorites.includes(model.name)
              const isLoaded = model.loaded || false

              return (
                <div
                  key={model.name}
                  className="flex items-center justify-between p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-primary-300 dark:hover:border-primary-700 transition-all"
                >
                  <div className="flex items-center gap-3 flex-1">
                    {/* Favorite star */}
                    <button
                      onClick={() => toggleFavorite(model.name)}
                      className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                      title={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
                    >
                      <Star
                        className={`w-4 h-4 ${
                          isFavorite
                            ? 'fill-yellow-400 text-yellow-400'
                            : 'text-gray-400 dark:text-gray-500'
                        }`}
                      />
                    </button>

                    {/* Model info */}
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {model.name}
                        </span>
                        {isFavorite && (
                          <span className="px-2 py-0.5 text-xs rounded-full bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200">
                            Favorite
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-3 mt-0.5">
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {model.size || 'Size unknown'}
                        </span>
                        {isLoaded && (
                          <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
                            <CheckCircle2 className="w-3 h-3" />
                            Loaded
                          </span>
                        )}
                        {!isLoaded && (
                          <span className="flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500">
                            <Circle className="w-3 h-3" />
                            Not loaded
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Load/Unload button */}
                    <button
                      onClick={() => isLoaded ? unloadModel(model.name) : preloadModel(model.name)}
                      className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                        isLoaded
                          ? 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                          : 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 hover:bg-primary-200 dark:hover:bg-primary-900/50'
                      }`}
                    >
                      {isLoaded ? 'Unload' : 'Load'}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* Download link */}
        {models.length > 0 && (
          <div className="mt-4 p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
            <p className="text-sm text-blue-900 dark:text-blue-100">
              Want more models?{' '}
              <a
                href="https://ollama.com/library"
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium underline hover:no-underline"
              >
                Browse Ollama Library
              </a>
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export default function ChatSettingsContent() {
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

          {/* Auto-preload default model */}
          <div className="flex items-center justify-between">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Auto-preload default model</label>
              <p className="text-xs text-gray-500 dark:text-gray-400">Load model on startup (3s after login)</p>
            </div>
            <input
              type="checkbox"
              checked={settings.autoPreloadModel}
              onChange={(e) => updateSettings({ autoPreloadModel: e.target.checked })}
              className="w-4 h-4 rounded text-primary-600"
            />
          </div>

          {/* Context Window (locked) */}
          <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
            <p className="text-sm font-medium text-gray-900 dark:text-gray-100">Context Window: 200k tokens</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Full conversation history sent to model for optimal context preservation</p>
          </div>
        </div>
      </div>

      {/* Model Manager Section */}
      <ModelManagerSection />
    </div>
  )
}
