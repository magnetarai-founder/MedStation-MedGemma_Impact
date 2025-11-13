import { useEffect, useState } from 'react'
import { ChevronDown, XCircle, Star, AlertCircle, Shield } from 'lucide-react'
import { useChatStore } from '../stores/chatStore'
import { useUserModelPrefsStore } from '../stores/userModelPrefsStore'
import { useTeamStore } from '../stores/teamStore'
import { api, authFetch } from '../lib/api'
import { parseModelSizeGB, canModelFit } from '../lib/models'
import { showActionToast, showToast } from '../lib/toast'

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
  const { currentTeam } = useTeamStore()
  const [modelStatuses, setModelStatuses] = useState<ModelStatus[]>([])
  const [usableMemoryGb, setUsableMemoryGb] = useState<number>(0)
  const [allowedModels, setAllowedModels] = useState<string[] | null>(null) // null = no policy (allow all)

  useEffect(() => {
    loadModels()
    loadModelStatuses()
    loadAll() // Load user preferences, catalog, and hot slots
  }, [])

  // Load team model policy (Sprint 5)
  useEffect(() => {
    if (currentTeam?.team_id) {
      loadTeamPolicy(currentTeam.team_id)
    } else {
      setAllowedModels(null) // No team context, allow all
    }
  }, [currentTeam?.team_id])

  const loadTeamPolicy = async (teamId: string) => {
    try {
      const response = await authFetch(`/api/v1/teams/${teamId}/model-policy`)
      if (response.ok) {
        const policy = await response.json()
        // If no models specified, treat as "allow all"
        if (policy.allowed_models && policy.allowed_models.length > 0) {
          setAllowedModels(policy.allowed_models)
        } else {
          setAllowedModels(null)
        }
      }
    } catch (error) {
      console.debug('Failed to load team policy (may not have permission):', error)
      setAllowedModels(null) // Fallback to allow all on error
    }
  }

  const loadModels = async () => {
    try {
      const response = await authFetch('/api/v1/chat/models')
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
      const response = await authFetch('/api/v1/chat/models/status')
      if (response.ok) {
        const data = await response.json()
        // Only show available (chat) models in selector
        setModelStatuses(data.available || [])
      }
    } catch (error) {
      console.debug('Failed to load model statuses:', error)
    }
  }

  // Load usable memory once (for memory-fit checks)
  useEffect(() => {
    const loadMemory = async () => {
      try {
        const res = await authFetch('/api/v1/chat/system/memory')
        if (res.ok) {
          const data = await res.json()
          setUsableMemoryGb(data.usable_for_models_gb || 0)
        }
      } catch {}
    }
    loadMemory()
  }, [])

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

  // Check if model is allowed by team policy (Sprint 5)
  const isModelAllowed = (modelName: string): boolean => {
    // If no policy (null), allow all
    if (allowedModels === null) return true
    // Otherwise check if model is in allowed list
    return allowedModels.includes(modelName)
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
      const response = await authFetch(
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

  const handleChange = async (name: string) => {
    if (!name) { onChange(''); return }

    // Check team policy (Sprint 5)
    if (!isModelAllowed(name)) {
      showToast.error(
        `Model '${name}' is not allowed by team policy. Ask your team admin to add it to the allowed list.`,
        5000
      )
      return
    }

    // Prevent selecting not-installed models
    if (!isModelInstalled(name)) {
      showActionToast(
        `Model '${name}' is not installed`,
        'Install Model',
        () => {
          // Dispatch custom event to open Model Management sidebar
          window.dispatchEvent(new CustomEvent('openModelManagement'))
        },
        { type: 'warning', duration: 5000 }
      )
      return
    }

    // Memory-fit check: if model not already loaded, ensure it fits
    const selected = modelStatuses.find(m => m.name === name)
    const alreadyLoaded = !!selected?.loaded
    if (!alreadyLoaded) {
      const currentUsed = modelStatuses.filter(m => m.loaded).reduce((sum, m) => sum + parseModelSizeGB(m.size), 0)
      const selectedSize = parseModelSizeGB(selected?.size || '0 GB')
      const fit = canModelFit(currentUsed, selectedSize, usableMemoryGb)
      if (!fit.fits) {
        showActionToast(
          `Model '${name}' exceeds memory budget`,
          'View Details',
          () => {
            showToast.warning(`${fit.reason}`, 5000)
          },
          { type: 'warning', duration: 5000 }
        )
        return
      }
    }

    onChange(name)
  }

  return (
    <div className="flex items-center gap-1">
      <div className="relative flex items-center">
        <select
          value={value}
          onChange={(e) => handleChange(e.target.value)}
          className="appearance-none bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 pl-3 pr-8 py-1 rounded border border-gray-300 dark:border-gray-700 focus:outline-none focus:ring-1 focus:ring-primary-500 cursor-pointer text-xs hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
        >
          <option value="">Select Model</option>
          {loadedModels.length === 0 ? (
            <option value="" disabled>No visible models loaded</option>
          ) : (
            loadedModels.map((model) => {
              const allowed = isModelAllowed(model.name)

              // Build display text with hot slot badge and indicators
              let displayText = ''

              // Hot slot badge (1-4)
              if (model.hotSlot !== null) {
                displayText += `[${model.hotSlot}] `
              }

              // Model name
              displayText += model.name

              // Policy indicator (Sprint 5)
              if (!allowed) {
                displayText += ' 🔒'
              }

              // Not-installed indicator
              if (!model.installed) {
                displayText += ' ⚠️'
              }

              return (
                <option
                  key={model.name}
                  value={model.name}
                  disabled={!allowed}
                  title={!allowed ? 'Not allowed by team policy' : undefined}
                >
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
        <div
          className="flex items-center gap-1 px-2 py-0.5 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 rounded text-xs"
          aria-label={`Hot slot ${getHotSlotNumber(value)} - favorite model`}
          role="status"
        >
          <Star className="w-3 h-3 fill-current" aria-hidden="true" />
          <span>{getHotSlotNumber(value)}</span>
        </div>
      )}

      {/* Policy violation warning (Sprint 5) */}
      {value && !isModelAllowed(value) && (
        <div
          className="flex items-center gap-1 px-2 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded text-xs"
          title="Not allowed by team policy"
          aria-label="Warning: Not allowed by team policy"
          role="alert"
        >
          <Shield className="w-3 h-3" aria-hidden="true" />
          <span>Policy</span>
        </div>
      )}

      {/* Not-installed warning (visible when model selected but not installed) */}
      {value && !isModelInstalled(value) && (
        <div
          className="flex items-center gap-1 px-2 py-0.5 bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 rounded text-xs"
          title="Model not installed in Ollama"
          aria-label="Warning: Model not installed in Ollama"
          role="alert"
        >
          <AlertCircle className="w-3 h-3" aria-hidden="true" />
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
