import { useState, useEffect } from 'react'
import { X, Cpu, Loader2, ChevronRight } from 'lucide-react'
import { api, authFetch } from '../lib/api'

interface ModelStatus {
  name: string
  loaded: boolean
  slot_number: number | null  // Which hot slot (1-4) the model is assigned to, or null if not assigned
  size: string
  modified_at?: string
  unavailable_reason?: string  // Reason why model is unavailable (for embedding/foundation models)
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
  const [unavailableModels, setUnavailableModels] = useState<ModelStatus[]>([])
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

  // Handle ESC key to close sidebar
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }

    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])

  const loadSystemMemory = async () => {
    try {
      const response = await authFetch('/api/v1/chat/system/memory')
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
        const availableModels = data.available || []
        const unavailableModelsList = data.unavailable || []

        setModels(availableModels)
        setUnavailableModels(unavailableModelsList)

        // Auto-populate hot slots with loaded models (only from available models)
        const loadedModels = availableModels.filter((m: ModelStatus) => m.loaded)
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

  const loadModelToSlot = async (model: ModelStatus, slotNumber: number) => {
    try {
      // Call API to assign model to specific slot
      const response = await authFetch(
        `/api/v1/chat/models/hot-slots/${slotNumber}?model_name=${encodeURIComponent(model.name)}`,
        { method: 'POST' }
      )

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(errorData.detail || `Failed to load model: ${response.statusText}`)
      }

      // Optimistically update UI
      const newSlots = [...hotSlots]
      newSlots[slotNumber - 1] = { slotNumber, model: { ...model, loaded: true, slot_number: slotNumber } }
      setHotSlots(newSlots)

      // Refresh to get updated status
      setTimeout(() => loadModels(), 1000)
    } catch (error) {
      console.error('Failed to load model:', error)
      alert(`Failed to load model to slot ${slotNumber}: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  const ejectModel = async (slotIndex: number) => {
    const slot = hotSlots[slotIndex]
    if (!slot.model) return

    const slotNumber = slotIndex + 1

    try {
      // Call API to remove from hot slot (which also unloads)
      const response = await authFetch(
        `/api/v1/chat/models/hot-slots/${slotNumber}`,
        { method: 'DELETE' }
      )

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(errorData.detail || `Failed to eject model: ${response.statusText}`)
      }

      // Optimistically update UI
      const newSlots = [...hotSlots]
      newSlots[slotIndex] = { slotNumber, model: null }
      setHotSlots(newSlots)

      // Refresh to get updated status
      setTimeout(() => loadModels(), 1000)
    } catch (error) {
      console.error('Failed to eject model:', error)
      alert(`Failed to eject model: ${error instanceof Error ? error.message : 'Unknown error'}`)
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

  // Get occupied slots (for graying out slot buttons)
  const occupiedSlots = hotSlots.map(slot => slot.model !== null ? slot.slotNumber : null).filter(Boolean) as number[]

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop - no click to close, prevents accidental closing */}
      <div
        className="fixed inset-0 bg-black/30 backdrop-blur-sm z-40"
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
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v15m6-15v15M3 18h18M3 7l6-4 6 4 6-4v11H3V7z" />
                      </svg>
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
              {/* Browse More Models Link */}
              <div className="p-4 rounded-lg bg-gradient-to-r from-primary-50 to-blue-50 dark:from-primary-900/20 dark:to-blue-900/20 border border-primary-200 dark:border-primary-800">
                <a
                  href="https://ollama.com/library"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between group"
                >
                  <div>
                    <h4 className="text-sm font-semibold text-primary-900 dark:text-primary-100">
                      Browse More Models
                    </h4>
                    <p className="text-xs text-primary-700 dark:text-primary-300 mt-0.5">
                      Explore the Ollama model library
                    </p>
                  </div>
                  <ChevronRight className="w-5 h-5 text-primary-600 dark:text-primary-400 group-hover:translate-x-1 transition-transform" />
                </a>
              </div>

              {/* All Models Section */}
              <div>
                <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
                  Available Models ({availableModels.length})
                </h3>
                <div className="space-y-2">
                  {availableModels.map((model) => (
                    <AvailableModelCard
                      key={model.name}
                      model={model}
                      onLoad={loadModelToSlot}
                      formatFileSize={formatFileSize}
                      occupiedSlots={occupiedSlots}
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
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Unavailable Models Section (Embedding/Foundation) */}
              {unavailableModels.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Unavailable ({unavailableModels.length})
                    </h3>
                    <div className="group relative">
                      <button className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                        </svg>
                      </button>
                      <div className="absolute left-0 top-full mt-2 w-80 p-3 bg-gray-900 dark:bg-gray-800 text-white text-xs rounded-lg shadow-xl opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto transition-opacity z-50 border border-gray-700">
                        <h4 className="font-semibold text-sm mb-2">Why are these unavailable?</h4>
                        <div className="space-y-2">
                          <div>
                            <span className="font-medium text-blue-300">Embedding Models:</span>
                            <p className="text-gray-300 mt-0.5">Convert text to vectors for semantic search. Not designed for conversation.</p>
                          </div>
                          <div>
                            <span className="font-medium text-purple-300">Foundation Models:</span>
                            <p className="text-gray-300 mt-0.5">Base models without instruction tuning. Use their instruct variants instead.</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="space-y-2">
                    {unavailableModels.map((model) => {
                      const isEmbedding = model.unavailable_reason?.includes('Embedding')
                      const isFoundation = model.unavailable_reason?.includes('Foundation')

                      return (
                        <div
                          key={model.name}
                          className="flex items-center gap-3 p-3 bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-800/30 dark:to-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700"
                        >
                          {/* Model Info */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">
                                {model.name}
                              </h4>
                              {isEmbedding && (
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
                                  Embedding
                                </span>
                              )}
                              {isFoundation && (
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300">
                                  Foundation
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                              {formatFileSize(model.size)}
                            </p>
                          </div>

                          {/* Info Icon with Tooltip */}
                          <div className="group/info relative flex-shrink-0">
                            <button className="p-2 rounded-lg text-gray-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all">
                              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                              </svg>
                            </button>
                            <div className="absolute right-0 top-full mt-2 w-72 p-3 bg-gray-900 dark:bg-gray-800 text-white text-xs rounded-lg shadow-xl opacity-0 pointer-events-none group-hover/info:opacity-100 group-hover/info:pointer-events-auto transition-opacity z-50 border border-gray-700">
                              {isEmbedding && (
                                <div>
                                  <h5 className="font-semibold text-blue-300 mb-1">Embedding Model</h5>
                                  <p className="text-gray-300 mb-2">
                                    This model converts text into numerical vectors for semantic similarity search and document retrieval.
                                  </p>
                                  <p className="text-gray-400 text-xs">
                                    <strong>Use case:</strong> Document search, RAG pipelines, similarity matching
                                  </p>
                                </div>
                              )}
                              {isFoundation && (
                                <div>
                                  <h5 className="font-semibold text-purple-300 mb-1">Foundation Model</h5>
                                  <p className="text-gray-300 mb-2">
                                    Base model without instruction tuning. Cannot follow instructions or engage in conversation.
                                  </p>
                                  <p className="text-gray-400 text-xs">
                                    <strong>Tip:</strong> Look for variants with "instruct", "chat", or "it" suffixes instead
                                  </p>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      )
                    })}
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
  onLoad: (model: ModelStatus, slotNumber: number) => void
  formatFileSize: (size: string) => string
  occupiedSlots: number[]
}

function AvailableModelCard({ model, onLoad, formatFileSize, occupiedSlots }: AvailableModelCardProps) {
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

      {/* Slot Assignment Buttons [1][2][3][4] */}
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4].map((slotNum) => {
          const isOccupied = occupiedSlots.includes(slotNum)
          return (
            <button
              key={slotNum}
              onClick={() => !isOccupied && onLoad(model, slotNum)}
              disabled={isOccupied}
              className={`flex-shrink-0 w-7 h-7 rounded-md font-bold text-xs transition-all ${
                isOccupied
                  ? 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                  : 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 hover:bg-primary-200 dark:hover:bg-primary-800/50'
              }`}
              title={isOccupied ? `Slot ${slotNum} occupied` : `Load to slot ${slotNum}`}
            >
              {slotNum}
            </button>
          )
        })}
      </div>
    </div>
  )
}
