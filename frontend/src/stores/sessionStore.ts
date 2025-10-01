import { create } from 'zustand'
import type { FileUploadResponse, QueryResponse } from '@/lib/api'

interface SessionState {
  sessionId: string | null
  currentFile: FileUploadResponse | null
  currentQuery: QueryResponse | null
  isExecuting: boolean
  exportFormat: 'excel' | 'csv' | 'json' | 'parquet'
  
  setSessionId: (id: string) => void
  setCurrentFile: (file: FileUploadResponse | null) => void
  setCurrentQuery: (query: QueryResponse | null) => void
  setIsExecuting: (executing: boolean) => void
  setExportFormat: (format: 'excel' | 'csv' | 'json' | 'parquet') => void
  clearSession: () => void
}

export const useSessionStore = create<SessionState>((set) => ({
  sessionId: null,
  currentFile: null,
  currentQuery: null,
  isExecuting: false,
  exportFormat: 'excel',
  
  setSessionId: (id) => set({ sessionId: id }),
  setCurrentFile: (file) => set({ currentFile: file }),
  setCurrentQuery: (query) => set({ currentQuery: query }),
  setIsExecuting: (executing) => set({ isExecuting: executing }),
  setExportFormat: (format) => set({ exportFormat: format }),
  clearSession: () => set({
    sessionId: null,
    currentFile: null,
    currentQuery: null,
    isExecuting: false,
    exportFormat: 'excel',
  }),
}))