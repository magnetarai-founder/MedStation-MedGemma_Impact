import { createWithEqualityFn } from 'zustand/traditional'

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

export const useLogsStore = createWithEqualityFn<LogsState>((set) => ({
  logs: [],
  appendLog: (entry) => set((s) => ({ logs: [...s.logs, entry] })),
  clearLogs: () => set({ logs: [] }),
}))

