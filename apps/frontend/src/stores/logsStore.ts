import { create } from 'zustand'

export type LogLevel = 'info' | 'warning' | 'error' | 'success'

export interface LogEntry {
  id: string
  timestamp: string
  level: LogLevel
  message: string
}

interface LogsState {
  logs: LogEntry[]
  appendLog: (entry: LogEntry) => void
  clearLogs: () => void
}

export const useLogsStore = create<LogsState>((set) => ({
  logs: [],
  appendLog: (entry) => set((s) => ({ logs: [...s.logs, entry] })),
  clearLogs: () => set({ logs: [] }),
}))

