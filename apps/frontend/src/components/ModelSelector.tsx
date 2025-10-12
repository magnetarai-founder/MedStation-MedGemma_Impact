import { useEffect, useState } from 'react'
import { ChevronDown, XCircle } from 'lucide-react'
import { useChatStore } from '../stores/chatStore'
import { api } from '../lib/api'

interface ModelSelectorProps {
  value: string
  onChange: (model: string) => void
}

interface ModelStatus {
  name: string
  loaded: boolean
  is_favorite: boolean
  size: string
}

export function ModelSelector({ value, onChange }: ModelSelectorProps) {
  const { availableModels, setAvailableModels } = useChatStore()
  const [modelStatuses, setModelStatuses] = useState<ModelStatus[]>([])

  useEffect(() => {
    loadModels()
    loadModelStatuses()
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
        setModelStatuses(data.models || [])
      }
    } catch (error) {
      console.debug('Failed to load model statuses:', error)
    }
  }

  const getModelStatus = (modelName: string) => {
    return modelStatuses.find(m => m.name === modelName)
  }

  const selectedModelStatus = getModelStatus(value)

  // Only show loaded models in dropdown
  const loadedModels = modelStatuses.filter(m => m.loaded)

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
    <div className="flex items-center gap-2">
      <div className="relative flex items-center gap-2">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="appearance-none bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 pl-4 pr-10 py-2 rounded-lg border border-gray-300 dark:border-gray-700 focus:outline-none focus:ring-2 focus:ring-primary-500 cursor-pointer text-sm font-medium hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
        >
          <option value="">Chat</option>
          {loadedModels.length === 0 ? (
            <option value="" disabled>No models loaded</option>
          ) : (
            loadedModels.map((model) => (
              <option key={model.name} value={model.name}>
                {model.is_favorite ? '⭐ ' : ''}{model.name}
              </option>
            ))
          )}
        </select>

        <ChevronDown
          size={16}
          className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-gray-500"
        />
      </div>

      {/* Eject button */}
      {value && (
        <button
          onClick={handleEject}
          className="p-2 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors text-gray-400 hover:text-red-500"
          title="Eject model"
        >
          <XCircle size={18} />
        </button>
      )}
    </div>
  )
}
