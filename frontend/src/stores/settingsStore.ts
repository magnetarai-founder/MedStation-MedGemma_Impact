import { create } from 'zustand'

interface SettingsState {
  // SQL tab settings
  previewRowCount: number
  setPreviewRowCount: (n: number) => void

  // JSON tab settings
  jsonExpandArrays: boolean
  jsonMaxDepth: number
  jsonAutoSafe: boolean
  setJsonExpandArrays: (v: boolean) => void
  setJsonMaxDepth: (n: number) => void
  setJsonAutoSafe: (v: boolean) => void

  // Chat tab settings
  chatAutoTitle: boolean
  chatContextWindow: number
  setChatAutoTitle: (v: boolean) => void
  setChatContextWindow: (n: number) => void
}

const PREVIEW_KEY = 'ns.previewRowCount'
const JSON_EXPAND_KEY = 'ns.jsonExpandArrays'
const JSON_DEPTH_KEY = 'ns.jsonMaxDepth'
const JSON_SAFE_KEY = 'ns.jsonAutoSafe'
const CHAT_AUTO_TITLE_KEY = 'ns.chatAutoTitle'
const CHAT_CONTEXT_KEY = 'ns.chatContextWindow'

export const useSettingsStore = create<SettingsState>((set) => ({
  // SQL settings
  previewRowCount: Number(localStorage.getItem(PREVIEW_KEY)) || 100,
  setPreviewRowCount: (n: number) => {
    localStorage.setItem(PREVIEW_KEY, String(n))
    set({ previewRowCount: n })
  },

  // JSON settings
  jsonExpandArrays: localStorage.getItem(JSON_EXPAND_KEY) !== 'false',
  jsonMaxDepth: Number(localStorage.getItem(JSON_DEPTH_KEY)) || 5,
  jsonAutoSafe: localStorage.getItem(JSON_SAFE_KEY) !== 'false',
  setJsonExpandArrays: (v: boolean) => {
    localStorage.setItem(JSON_EXPAND_KEY, String(v))
    set({ jsonExpandArrays: v })
  },
  setJsonMaxDepth: (n: number) => {
    localStorage.setItem(JSON_DEPTH_KEY, String(n))
    set({ jsonMaxDepth: n })
  },
  setJsonAutoSafe: (v: boolean) => {
    localStorage.setItem(JSON_SAFE_KEY, String(v))
    set({ jsonAutoSafe: v })
  },

  // Chat settings
  chatAutoTitle: localStorage.getItem(CHAT_AUTO_TITLE_KEY) !== 'false',
  chatContextWindow: Number(localStorage.getItem(CHAT_CONTEXT_KEY)) || 50,
  setChatAutoTitle: (v: boolean) => {
    localStorage.setItem(CHAT_AUTO_TITLE_KEY, String(v))
    set({ chatAutoTitle: v })
  },
  setChatContextWindow: (n: number) => {
    localStorage.setItem(CHAT_CONTEXT_KEY, String(n))
    set({ chatContextWindow: n })
  },
}))

