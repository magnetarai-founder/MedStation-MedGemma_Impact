import { useEffect } from 'react'
import { ChevronDown } from 'lucide-react'
import { useChatStore } from '../stores/chatStore'
import { api } from '../lib/api'

interface ModelSelectorProps {
  value: string
  onChange: (model: string) => void
}

export function ModelSelector({ value, onChange }: ModelSelectorProps) {
  const { availableModels, setAvailableModels } = useChatStore()

  useEffect(() => {
    loadModels()
  }, [])

  const loadModels = async () => {
    try {
      const response = await fetch(`${api.BASE_URL}/api/v1/chat/models`)
      if (response.ok) {
        const models = await response.json()
        setAvailableModels(models)
      }
    } catch (error) {
      console.error('Failed to load models:', error)
    }
  }

  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="appearance-none bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-4 py-2 pr-10 rounded-lg border border-gray-300 dark:border-gray-700 focus:outline-none focus:ring-2 focus:ring-primary-500 cursor-pointer text-sm font-medium"
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

      <ChevronDown
        size={16}
        className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-gray-500"
      />
    </div>
  )
}
