/**
 * OmniStudio History Store - API-backed with SQLite
 * Replaces localStorage-based history with scalable SQLite backend
 */

import { create } from 'zustand'
import * as historyApi from '@/lib/historyApi'

export interface HistoryItem {
  id: number
  query: string
  type: 'sql' | 'json'
  timestamp: number // Converted from ISO string
  executionTime?: number
  rowCount?: number
}

interface HistoryStore {
  // State
  isLoading: boolean
  error: string | null

  // Actions
  addToHistory: (item: Omit<HistoryItem, 'id' | 'timestamp'>) => Promise<void>
  clearHistory: () => Promise<void>
  deleteHistoryItem: (id: number) => Promise<void>
}

export const useHistoryStore = create<HistoryStore>((set, get) => ({
  isLoading: false,
  error: null,

  addToHistory: async (item) => {
    try {
      set({ isLoading: true, error: null })

      await historyApi.addToHistory({
        query: item.query,
        query_type: item.type,
        execution_time: item.executionTime,
        row_count: item.rowCount,
        success: true,
      })

      set({ isLoading: false })
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Failed to add to history'
      set({ error: errorMsg, isLoading: false })
      console.error('Failed to add to history:', error)
    }
  },

  clearHistory: async () => {
    try {
      set({ isLoading: true, error: null })
      await historyApi.clearHistory()
      set({ isLoading: false })
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Failed to clear history'
      set({ error: errorMsg, isLoading: false })
      console.error('Failed to clear history:', error)
    }
  },

  deleteHistoryItem: async (id) => {
    try {
      set({ isLoading: true, error: null })
      await historyApi.deleteHistoryItem(id)
      set({ isLoading: false })
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Failed to delete history item'
      set({ error: errorMsg, isLoading: false })
      console.error('Failed to delete history item:', error)
    }
  },
}))
