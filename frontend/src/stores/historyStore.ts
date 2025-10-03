import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface HistoryItem {
  id: string
  query: string
  type: 'sql' | 'json'
  timestamp: number
  executionTime?: number
  rowCount?: number
}

interface HistoryStore {
  history: HistoryItem[]
  addToHistory: (item: Omit<HistoryItem, 'id' | 'timestamp'>) => void
  clearHistory: () => void
  deleteHistoryItem: (id: string) => void
}

// Get max history from settings or default to 100
const getMaxHistoryItems = () => {
  try {
    const stored = localStorage.getItem('ns.maxHistoryItems')
    return stored ? JSON.parse(stored) : 100
  } catch {
    return 100
  }
}

export const useHistoryStore = create<HistoryStore>()(
  persist(
    (set) => ({
      history: [],

      addToHistory: (item) => set((state) => {
        const newItem: HistoryItem = {
          ...item,
          id: `history_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          timestamp: Date.now(),
        }

        // Keep only last N items (from settings)
        const maxItems = getMaxHistoryItems()
        const updatedHistory = [newItem, ...state.history].slice(0, maxItems)

        return { history: updatedHistory }
      }),

      clearHistory: () => set({ history: [] }),

      deleteHistoryItem: (id) => set((state) => ({
        history: state.history.filter(item => item.id !== id)
      })),
    }),
    {
      name: 'ns.queryHistory',
    }
  )
)
