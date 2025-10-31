import { useEffect, useRef } from 'react'
import { useChatStore } from '../stores/chatStore'

/**
 * Custom hook for syncing model availability across the entire app
 *
 * Polls the /api/v1/chat/models/status endpoint every 5 seconds
 * and updates the chatStore when models change (load/unload).
 *
 * This ensures ALL model dropdowns across the app stay in sync
 * without requiring page refreshes.
 *
 * Usage: Call once in App.tsx to enable global model syncing
 */
export function useModelSync(intervalMs: number = 5000) {
  const { setAvailableModels } = useChatStore()
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  const previousModelsRef = useRef<string>('')

  useEffect(() => {
    const syncModels = async () => {
      try {
        const response = await fetch('/api/v1/chat/models/status')
        if (!response.ok) {
          console.debug('Model sync: Failed to fetch models status')
          return
        }

        const data = await response.json()
        const availableModels = data.available || []

        // Convert to comparable string to detect changes
        const currentModelsString = JSON.stringify(
          availableModels.map((m: any) => ({
            name: m.name,
            loaded: m.loaded,
            slot_number: m.slot_number
          })).sort((a: any, b: any) => a.name.localeCompare(b.name))
        )

        // Only update if models have actually changed
        if (currentModelsString !== previousModelsRef.current) {
          console.log('Model sync: Models changed, updating store')

          // Update chatStore with available models (name + size for dropdowns)
          const modelsForDropdown = availableModels.map((m: any) => ({
            name: m.name,
            size: m.size || 'Unknown'
          }))

          setAvailableModels(modelsForDropdown)
          previousModelsRef.current = currentModelsString
        }
      } catch (error) {
        console.debug('Model sync: Error syncing models:', error)
      }
    }

    // Initial sync
    syncModels()

    // Set up polling interval
    intervalRef.current = setInterval(syncModels, intervalMs)

    // Cleanup
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [intervalMs, setAvailableModels])
}
