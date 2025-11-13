import { useEffect, useState } from 'react'
import { ChevronDown, XCircle, Star, AlertCircle } from 'lucide-react'
import { useChatStore } from '../stores/chatStore'
import { useUserModelPrefsStore } from '../stores/userModelPrefsStore'
import { api } from '../lib/api'

interface ModelSelectorProps {
  value: string
  onChange: (model: string) => void
}

interface ModelStatus {
  name: string
  loaded: boolean
  slot_number: number | null
  size: string
}

export function ModelSelector({ value, onChange }: ModelSelectorProps) {
  const { availableModels, setAvailableModels } = useChatStore()
  const { catalog, getVisibleModels, hotSlots, loadAll } = useUserModelPrefsStore()
  const [modelStatuses, setModelStatuses] = useState<ModelStatus[]>([])

  useEffect(() => {
    loadModels()
    loadModelStatuses()
    loadAll() // Load user preferences, catalog, and hot slots
  }, [])

  const loadModels = async () => {
    try {
      const response = await fetch('/api/v1/chat/models')
      if (response.ok) {
        const models = await response.json()
        setAvailableModels(models)
      }
    } catch (error) {
      console.error('Failed to load models:', error)
    }
  }

  const loadModelStatuses = async () => {
    try {
      const response = await fetch('/api/v1/chat/models/status')
      if (response.ok) {
        const data = await response.json()
        // Only show available (chat) models in selector
        setModelStatuses(data.available || [])
      }
    } catch (error) {
      console.debug('Failed to load model statuses:', error)
    }
  }

  const getModelStatus = (modelName: string) => {
    return modelStatuses.find(m => m.name === modelName)
  }

  // Get hot slot number for a model (1-4)
  const getHotSlotNumber = (modelName: string): number | null => {
    for (const [slotNum, model] of Object.entries(hotSlots)) {
      if (model === modelName) {
        return parseInt(slotNum)
      }
    }
    return null
  }

  // Check if model is installed in the catalog
  const isModelInstalled = (modelName: string): boolean => {
    const catalogEntry = catalog.find(m => m.model_name === modelName)
    return catalogEntry?.status === 'installed'
  }

  const selectedModelStatus = getModelStatus(value)

  // Get visible models from user preferences
  const visibleModels = getVisibleModels()
  const visibleModelNames = new Set(visibleModels.map(m => m.model_name))

  // Filter to only show visible models that are loaded
  const loadedModels = modelStatuses
    .filter(m => m.loaded && visibleModelNames.has(m.name))
    .map(m => ({
      ...m,
      hotSlot: getHotSlotNumber(m.name),
      installed: isModelInstalled(m.name)
    }))
    .sort((a, b) => {
      // Sort: hot slot models first (1→4), then alphabetically
      if (a.hotSlot !== null && b.hotSlot === null) return -1
      if (a.hotSlot === null && b.hotSlot !== null) return 1
      if (a.hotSlot !== null && b.hotSlot !== null) return a.hotSlot - b.hotSlot
      return a.name.localeCompare(b.name)
    })

  const handleEject = async () => {
    if (!value) return

    try {
      const response = await fetch(
        `/api/v1/chat/models/unload/${encodeURIComponent(value)}`,
        { method: 'POST' }
      )

      if (response.ok) {
        onChange('') // Clear selection
        // Reload model statuses to reflect changes
        await loadModelStatuses()
      } else {
        console.error('Failed to unload model')
      }
    } catch (error) {
      console.error('Error unloading model:', error)
    }
  }

  return (
    <div className="flex items-center gap-1">
      <div className="relative flex items-center">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="appearance-none bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 pl-3 pr-8 py-1 rounded border border-gray-300 dark:border-gray-700 focus:outline-none focus:ring-1 focus:ring-primary-500 cursor-pointer text-xs hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
        >
          <option value="">Select Model</option>
          {loadedModels.length === 0 ? (
            <option value="" disabled>No visible models loaded</option>
          ) : (
            loadedModels.map((model) => {
              // Build display text with hot slot badge and not-installed indicator
              let displayText = ''

              // Hot slot badge (1-4)
              if (model.hotSlot !== null) {
                displayText += `[${model.hotSlot}] `
              }

              // Model name
              displayText += model.name

              // Not-installed indicator
              if (!model.installed) {
                displayText += ' ⚠️'
              }

              return (
                <option key={model.name} value={model.name}>
                  {displayText}
                </option>
              )
            })
          )}
        </select>

        <ChevronDown
          size={14}
          className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-gray-500"
        />
      </div>

      {/* Hot slot badge indicator (visible when model selected) */}
      {value && getHotSlotNumber(value) !== null && (
        <div className="flex items-center gap-1 px-2 py-0.5 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 rounded text-xs">
          <Star className="w-3 h-3 fill-current" />
          <span>{getHotSlotNumber(value)}</span>
        </div>
      )}

      {/* Not-installed warning (visible when model selected but not installed) */}
      {value && !isModelInstalled(value) && (
        <div className="flex items-center gap-1 px-2 py-0.5 bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 rounded text-xs" title="Model not installed in Ollama">
          <AlertCircle className="w-3 h-3" />
          <span>Not installed</span>
        </div>
      )}

      {/* Eject button */}
      {value && (
        <button
          onClick={handleEject}
          className="p-1 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors text-gray-400 hover:text-red-500"
          title="Eject model"
        >
          <XCircle size={14} />
        </button>
      )}
    </div>
  )
}
