import { create } from 'zustand'

export interface OllamaServerState {
  running: boolean
  loadedModels: string[]
  modelCount: number
}

interface OllamaStore {
  serverStatus: OllamaServerState
  setServerStatus: (status: OllamaServerState) => void
  fetchServerStatus: () => Promise<void>
}

export const useOllamaStore = create<OllamaStore>()((set) => ({
  serverStatus: {
    running: false,
    loadedModels: [],
    modelCount: 0
  },

  setServerStatus: (status) => set({ serverStatus: status }),

  fetchServerStatus: async () => {
    try {
      const response = await fetch('/api/v1/chat/ollama/server/status')
      if (response.ok) {
        const data = await response.json()
        set({
          serverStatus: {
            running: data.running,
            loadedModels: data.loaded_models || [],
            modelCount: data.model_count || 0
          }
        })
      } else {
        set({
          serverStatus: {
            running: false,
            loadedModels: [],
            modelCount: 0
          }
        })
      }
    } catch (error) {
      console.error('Failed to fetch Ollama server status:', error)
      set({
        serverStatus: {
          running: false,
          loadedModels: [],
          modelCount: 0
        }
      })
    }
  }
}))
