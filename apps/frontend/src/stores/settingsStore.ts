import { createWithEqualityFn } from 'zustand/traditional'

type LogoAnimation = 'static' | 'pulsing'
type ExportFormat = 'excel' | 'csv' | 'parquet' | 'json'

interface SettingsState {
  // Display settings
  logoAnimation: LogoAnimation

  // Chat settings (ElohimOS)
  chatAutoTitle: boolean
  chatContextWindow: number

  // SQL settings
  previewRowCount: number

  // Performance settings (Neutron-Star)
  queryTimeout: number // seconds
  maxFileSize: number // MB
  memoryLimit: number // MB
  sessionTimeout: number // hours
  maxHistoryItems: number
  maxSavedQueries: number

  // Export settings (Neutron-Star)
  defaultExportFormat: ExportFormat
  exportFilenamePattern: string

  // JSON Conversion settings
  jsonExpandArrays: boolean
  jsonMaxDepth: number
  jsonAutoSafe: boolean
  jsonIncludeSummary: boolean

  // Setters
  setLogoAnimation: (animation: LogoAnimation) => void
  setChatAutoTitle: (v: boolean) => void
  setChatContextWindow: (n: number) => void
  setPreviewRowCount: (n: number) => void
  setQueryTimeout: (seconds: number) => void
  setMaxFileSize: (mb: number) => void
  setMemoryLimit: (mb: number) => void
  setSessionTimeout: (hours: number) => void
  setMaxHistoryItems: (n: number) => void
  setMaxSavedQueries: (n: number) => void
  setDefaultExportFormat: (format: ExportFormat) => void
  setExportFilenamePattern: (pattern: string) => void
  setJsonExpandArrays: (expand: boolean) => void
  setJsonMaxDepth: (depth: number) => void
  setJsonAutoSafe: (autoSafe: boolean) => void
  setJsonIncludeSummary: (include: boolean) => void
}

// Storage keys
const KEYS = {
  logoAnimation: 'ns.logoAnimation',
  chatAutoTitle: 'ns.chatAutoTitle',
  chatContextWindow: 'ns.chatContextWindow',
  previewRowCount: 'ns.previewRowCount',
  queryTimeout: 'ns.queryTimeout',
  maxFileSize: 'ns.maxFileSize',
  memoryLimit: 'ns.memoryLimit',
  sessionTimeout: 'ns.sessionTimeout',
  maxHistoryItems: 'ns.maxHistoryItems',
  maxSavedQueries: 'ns.maxSavedQueries',
  defaultExportFormat: 'ns.defaultExportFormat',
  exportFilenamePattern: 'ns.exportFilenamePattern',
  jsonExpandArrays: 'ns.jsonExpandArrays',
  jsonMaxDepth: 'ns.jsonMaxDepth',
  jsonAutoSafe: 'ns.jsonAutoSafe',
  jsonIncludeSummary: 'ns.jsonIncludeSummary',
}

// Helper functions
const getItem = <T>(key: string, defaultValue: T): T => {
  const stored = localStorage.getItem(key)
  if (stored === null) return defaultValue
  try {
    return JSON.parse(stored) as T
  } catch {
    return defaultValue
  }
}

const setItem = <T>(key: string, value: T) => {
  localStorage.setItem(key, JSON.stringify(value))
}

export const useSettingsStore = createWithEqualityFn<SettingsState>((set) => ({
  // Display
  logoAnimation: getItem(KEYS.logoAnimation, 'pulsing'),

  // Chat (ElohimOS)
  chatAutoTitle: getItem(KEYS.chatAutoTitle, true),
  chatContextWindow: getItem(KEYS.chatContextWindow, 50),

  // SQL
  previewRowCount: getItem(KEYS.previewRowCount, 100),

  // Performance (Neutron-Star)
  queryTimeout: getItem(KEYS.queryTimeout, 300),
  maxFileSize: getItem(KEYS.maxFileSize, 1000),
  memoryLimit: getItem(KEYS.memoryLimit, 4096),
  sessionTimeout: getItem(KEYS.sessionTimeout, 24),
  maxHistoryItems: getItem(KEYS.maxHistoryItems, 100),
  maxSavedQueries: getItem(KEYS.maxSavedQueries, 100),

  // Export (Neutron-Star)
  defaultExportFormat: getItem(KEYS.defaultExportFormat, 'excel'),
  exportFilenamePattern: getItem(KEYS.exportFilenamePattern, 'omni_export_{date}'),

  // JSON Conversion
  jsonExpandArrays: getItem(KEYS.jsonExpandArrays, true),
  jsonMaxDepth: getItem(KEYS.jsonMaxDepth, 5),
  jsonAutoSafe: getItem(KEYS.jsonAutoSafe, true),
  jsonIncludeSummary: getItem(KEYS.jsonIncludeSummary, true),

  // Setters
  setLogoAnimation: (animation) => {
    setItem(KEYS.logoAnimation, animation)
    set({ logoAnimation: animation })
  },

  setChatAutoTitle: (v) => {
    setItem(KEYS.chatAutoTitle, v)
    set({ chatAutoTitle: v })
  },

  setChatContextWindow: (n) => {
    setItem(KEYS.chatContextWindow, n)
    set({ chatContextWindow: n })
  },

  setPreviewRowCount: (n) => {
    setItem(KEYS.previewRowCount, n)
    set({ previewRowCount: n })
  },

  setQueryTimeout: (seconds) => {
    setItem(KEYS.queryTimeout, seconds)
    set({ queryTimeout: seconds })
  },

  setMaxFileSize: (mb) => {
    setItem(KEYS.maxFileSize, mb)
    set({ maxFileSize: mb })
  },

  setMemoryLimit: (mb) => {
    setItem(KEYS.memoryLimit, mb)
    set({ memoryLimit: mb })
  },

  setSessionTimeout: (hours) => {
    setItem(KEYS.sessionTimeout, hours)
    set({ sessionTimeout: hours })
  },

  setMaxHistoryItems: (n) => {
    setItem(KEYS.maxHistoryItems, n)
    set({ maxHistoryItems: n })
  },

  setMaxSavedQueries: (n) => {
    setItem(KEYS.maxSavedQueries, n)
    set({ maxSavedQueries: n })
  },

  setDefaultExportFormat: (format) => {
    setItem(KEYS.defaultExportFormat, format)
    set({ defaultExportFormat: format })
  },

  setExportFilenamePattern: (pattern) => {
    setItem(KEYS.exportFilenamePattern, pattern)
    set({ exportFilenamePattern: pattern })
  },

  setJsonExpandArrays: (expand) => {
    setItem(KEYS.jsonExpandArrays, expand)
    set({ jsonExpandArrays: expand })
  },

  setJsonMaxDepth: (depth) => {
    setItem(KEYS.jsonMaxDepth, depth)
    set({ jsonMaxDepth: depth })
  },

  setJsonAutoSafe: (autoSafe) => {
    setItem(KEYS.jsonAutoSafe, autoSafe)
    set({ jsonAutoSafe: autoSafe })
  },

  setJsonIncludeSummary: (include) => {
    setItem(KEYS.jsonIncludeSummary, include)
    set({ jsonIncludeSummary: include })
  },
}))
