import { useState, useEffect } from 'react'
import { X, Star, Cpu, Loader2, XCircle, ChevronRight } from 'lucide-react'
import { api } from '../lib/api'

interface ModelStatus {
  name: string
  loaded: boolean
  is_favorite: boolean
  size: string
  modified_at?: string
}

interface HotSlot {
  slotNumber: number
  model: ModelStatus | null
}

interface ModelManagementSidebarProps {
  isOpen: boolean
  onClose: () => void
}

export function ModelManagementSidebar({ isOpen, onClose }: ModelManagementSidebarProps) {
  const [models, setModels] = useState<ModelStatus[]>([])
  const [loading, setLoading] = useState(false)
  const [systemMemoryGB, setSystemMemoryGB] = useState<number>(128) // Default fallback
  const [hotSlots, setHotSlots] = useState<HotSlot[]>([
    { slotNumber: 1, model: null },
    { slotNumber: 2, model: null },
    { slotNumber: 3, model: null },
    { slotNumber: 4, model: null },
  ])

  useEffect(() => {
    if (isOpen) {
      loadModels()
      loadSystemMemory()
    }
  }, [isOpen])

  const loadSystemMemory = async () => {
    try {
      const response = await fetch('/api/v1/chat/system/memory')
      if (response.ok) {
        const data = await response.json()
        setSystemMemoryGB(data.usable_for_models_gb || 128)
      }
    } catch (error) {
      console.error('Failed to load system memory:', error)
      // Keep default fallback value
    }
  }

  const loadModels = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/v1/chat/models/status')
      if (response.ok) {
        const data = await response.json()
        const modelList = data.models || []
        setModels(modelList)

        // Auto-populate hot slots with loaded models
        const loadedModels = modelList.filter((m: ModelStatus) => m.loaded)
        const newSlots = [...hotSlots]
        loadedModels.slice(0, 4).forEach((model: ModelStatus, idx: number) => {
          newSlots[idx] = { slotNumber: idx + 1, model }
        })
        setHotSlots(newSlots)
      }
    } catch (error) {
      console.error('Failed to load models:', error)
    } finally {
      setLoading(false)
    }
  }

  const toggleFavorite = async (modelName: string, isFavorite: boolean) => {
    try {
      const method = isFavorite ? 'DELETE' : 'POST'
      const response = await fetch(
        `/api/v1/chat/models/favorites/${encodeURIComponent(modelName)}`,
        { method }
      )

      if (response.ok) {
        await loadModels()
      }
    } catch (error) {
      console.error('Failed to toggle favorite:', error)
    }
  }

  const loadModelToSlot = async (model: ModelStatus) => {
    // Find empty slot
    const emptySlotIndex = hotSlots.findIndex(slot => slot.model === null)
    if (emptySlotIndex === -1) {
      alert('All 4 slots are full. Eject a model first.')
      return
    }

    try {
      // Call API to load model
      const response = await fetch(
        `/api/v1/chat/models/preload?model=${encodeURIComponent(model.name)}`,
        { method: 'POST' }
      )

      if (!response.ok) {
        throw new Error(`Failed to load model: ${response.statusText}`)
      }

      // Optimistically update UI
      const newSlots = [...hotSlots]
      newSlots[emptySlotIndex] = { ...newSlots[emptySlotIndex], model: { ...model, loaded: true } }
      setHotSlots(newSlots)

      // Refresh to get updated status
      setTimeout(() => loadModels(), 1000)
    } catch (error) {
      console.error('Failed to load model:', error)
      alert(`Failed to load model: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  const ejectModel = async (slotIndex: number) => {
    const slot = hotSlots[slotIndex]
    if (!slot.model) return

    try {
      // Call API to unload model
      const response = await fetch(
        `/api/v1/chat/models/unload/${encodeURIComponent(slot.model.name)}`,
        { method: 'POST' }
      )

      if (!response.ok) {
        throw new Error(`Failed to unload model: ${response.statusText}`)
      }

      // Optimistically update UI
      const newSlots = [...hotSlots]
      newSlots[slotIndex] = { slotNumber: slotIndex + 1, model: null }
      setHotSlots(newSlots)

      // Refresh to get updated status
      setTimeout(() => loadModels(), 1000)
    } catch (error) {
      console.error('Failed to unload model:', error)
      alert(`Failed to unload model: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  const formatFileSize = (size: string) => {
    const match = size.match(/^([\d.]+)\s*([A-Z]+)$/)
    if (!match) return size
    const value = parseFloat(match[1])
    const unit = match[2]
    return `${value.toFixed(1)} ${unit}`
  }

  // Get total loaded size in GB
  const getTotalLoadedSize = () => {
    const loadedModels = hotSlots.filter(slot => slot.model).map(slot => slot.model!)
    const total = loadedModels.reduce((sum, model) => {
      const match = model.size.match(/^([\d.]+)/)
      return sum + (match ? parseFloat(match[1]) : 0)
    }, 0)
    return total
  }

  // Parse model size to GB
  const parseModelSizeGB = (size: string): number => {
    const match = size.match(/^([\d.]+)\s*([A-Z]+)$/)
    if (!match) return 0
    const value = parseFloat(match[1])
    const unit = match[2]

    // Convert to GB
    if (unit === 'GB') return value
    if (unit === 'MB') return value / 1024
    return 0
  }

  // Get available memory from system API
  // This value is fetched from the backend which reads actual Mac RAM
  const getAvailableMemoryGB = () => {
    return systemMemoryGB
  }

  // Check if model can fit in remaining memory
  const canModelFit = (modelSize: string): boolean => {
    const currentUsed = getTotalLoadedSize()
    const availableMemory = getAvailableMemoryGB()
    const modelSizeGB = parseModelSizeGB(modelSize)

    return (currentUsed + modelSizeGB) <= availableMemory
  }

  // Filter available models (not in hot slots, and can fit in memory)
  const availableModels = models.filter(model => {
    const inSlot = hotSlots.some(slot => slot.model?.name === model.name)
    const fitsInMemory = canModelFit(model.size)
    return !inSlot && fitsInMemory
  })

  // Models that won't fit
  const modelsTooBig = models.filter(model => {
    const inSlot = hotSlots.some(slot => slot.model?.name === model.name)
    const fitsInMemory = canModelFit(model.size)
    return !inSlot && !fitsInMemory
  })

  const favorites = availableModels.filter(m => m.is_favorite)
  const others = availableModels.filter(m => !m.is_favorite)

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/30 backdrop-blur-sm z-40"
        onClick={onClose}
      />

      {/* Sidebar */}
      <div className="fixed right-0 top-0 bottom-0 w-[480px] bg-white/95 dark:bg-gray-900/95 backdrop-blur-xl border-l border-gray-200 dark:border-gray-700 shadow-2xl z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-primary-600" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Model Management
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X size={20} className="text-gray-500" />
          </button>
        </div>

        {/* Hot Slots Section */}
        <div className="flex-shrink-0 px-6 py-4 bg-gray-50/50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
              Hot Models (4 Slots)
            </h3>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {getTotalLoadedSize().toFixed(1)} / {getAvailableMemoryGB().toFixed(0)} GB
            </span>
          </div>

          <div className="space-y-2">
            {hotSlots.map((slot, index) => (
              <div
                key={slot.slotNumber}
                className="flex items-center gap-3 p-3 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700"
              >
                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-xs font-bold text-gray-600 dark:text-gray-400">
                  {slot.slotNumber}
                </div>

                {slot.model ? (
                  <>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                          {slot.model.name}
                        </h4>
                        <span className="text-xs px-1.5 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded font-medium">
                          Loaded
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {formatFileSize(slot.model.size)}
                      </p>
                    </div>

                    <button
                      onClick={() => ejectModel(index)}
                      className="flex-shrink-0 p-2 rounded-lg transition-all text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
                      title="Eject model"
                    >
                      <XCircle size={16} />
                    </button>
                  </>
                ) : (
                  <div className="flex-1 text-sm text-gray-400 dark:text-gray-500 italic">
                    Empty slot
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Available Models List */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
            </div>
          ) : (
            <div className="p-6 space-y-6">
              {/* Favorites Section */}
              {favorites.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
                    Favorites ({favorites.length})
                  </h3>
                  <div className="space-y-2">
                    {favorites.map((model) => (
                      <AvailableModelCard
                        key={model.name}
                        model={model}
                        onToggleFavorite={toggleFavorite}
                        onLoad={loadModelToSlot}
                        formatFileSize={formatFileSize}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* All Models Section */}
              <div>
                <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
                  Available Models ({others.length})
                </h3>
                <div className="space-y-2">
                  {others.map((model) => (
                    <AvailableModelCard
                      key={model.name}
                      model={model}
                      onToggleFavorite={toggleFavorite}
                      onLoad={loadModelToSlot}
                      formatFileSize={formatFileSize}
                    />
                  ))}
                </div>
              </div>

              {/* Models Too Big Section */}
              {modelsTooBig.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
                    Won't Fit ({modelsTooBig.length})
                  </h3>
                  <div className="space-y-2">
                    {modelsTooBig.map((model) => (
                      <div
                        key={model.name}
                        className="flex items-center gap-3 p-3 bg-gray-100 dark:bg-gray-800/50 rounded-xl border border-gray-300 dark:border-gray-700 opacity-50"
                      >
                        <div className="flex-1 min-w-0">
                          <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                            {model.name}
                          </h4>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                            {formatFileSize(model.size)} • Too large
                          </p>
                        </div>
                        <button
                          onClick={() => toggleFavorite(model.name, model.is_favorite)}
                          className={`flex-shrink-0 p-2 rounded-lg transition-all ${
                            model.is_favorite
                              ? 'text-yellow-500 hover:bg-yellow-50 dark:hover:bg-yellow-900/20'
                              : 'text-gray-400 hover:text-yellow-500 hover:bg-gray-100 dark:hover:bg-gray-700'
                          }`}
                        >
                          <Star size={16} className={model.is_favorite ? 'fill-current' : ''} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/50">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Press <kbd className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-xs font-mono">⌘M</kbd> to toggle
          </p>
        </div>
      </div>
    </>
  )
}

interface AvailableModelCardProps {
  model: ModelStatus
  onToggleFavorite: (name: string, isFavorite: boolean) => void
  onLoad: (model: ModelStatus) => void
  formatFileSize: (size: string) => string
}

function AvailableModelCard({ model, onToggleFavorite, onLoad, formatFileSize }: AvailableModelCardProps) {
  return (
    <div className="flex items-center gap-3 p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-600 transition-colors group">
      {/* Model Info */}
      <div className="flex-1 min-w-0">
        <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
          {model.name}
        </h4>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
          {formatFileSize(model.size)}
        </p>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1">
        {/* Favorite Button */}
        <button
          onClick={() => onToggleFavorite(model.name, model.is_favorite)}
          className={`flex-shrink-0 p-2 rounded-lg transition-all ${
            model.is_favorite
              ? 'text-yellow-500 hover:bg-yellow-50 dark:hover:bg-yellow-900/20'
              : 'text-gray-400 hover:text-yellow-500 hover:bg-gray-100 dark:hover:bg-gray-700'
          }`}
          title={model.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
        >
          <Star
            size={16}
            className={model.is_favorite ? 'fill-current' : ''}
          />
        </button>

        {/* Load Button */}
        <button
          onClick={() => onLoad(model)}
          className="flex-shrink-0 p-2 rounded-lg transition-all text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20"
          title="Load to hot slot"
        >
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  )
}
