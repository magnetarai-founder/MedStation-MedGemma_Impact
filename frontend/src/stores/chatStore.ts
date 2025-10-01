import { create } from 'zustand'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  files?: Array<{
    id: string
    original_name: string
    size: number
    type: string
  }>
  model?: string
  tokens?: number
}

export interface ChatSession {
  id: string
  title: string
  created_at: string
  updated_at: string
  model: string
  message_count: number
}

interface ChatStore {
  // Sessions
  sessions: ChatSession[]
  activeChatId: string | null

  // Messages for active chat
  messages: ChatMessage[]

  // UI state
  isLoading: boolean
  isSending: boolean
  streamingContent: string

  // Available models
  availableModels: Array<{ name: string; size: string }>

  // Actions
  setSessions: (sessions: ChatSession[]) => void
  setActiveChat: (chatId: string | null) => void
  setMessages: (messages: ChatMessage[]) => void
  addMessage: (message: ChatMessage) => void
  setStreamingContent: (content: string) => void
  appendStreamingContent: (chunk: string) => void
  clearStreamingContent: () => void
  setIsLoading: (loading: boolean) => void
  setIsSending: (sending: boolean) => void
  setAvailableModels: (models: Array<{ name: string; size: string }>) => void

  // Helpers
  getActiveSession: () => ChatSession | null
}

// Get last active chat from sessionStorage
const getStoredActiveChatId = (): string | null => {
  try {
    return sessionStorage.getItem('neutron-active-chat-id')
  } catch {
    return null
  }
}

// Store active chat in sessionStorage
const storeActiveChatId = (chatId: string | null) => {
  try {
    if (chatId) {
      sessionStorage.setItem('neutron-active-chat-id', chatId)
    } else {
      sessionStorage.removeItem('neutron-active-chat-id')
    }
  } catch {
    // Ignore storage errors
  }
}

export const useChatStore = create<ChatStore>((set, get) => ({
  // Initial state - try to restore last active chat from session
  sessions: [],
  activeChatId: getStoredActiveChatId(),
  messages: [],
  isLoading: false,
  isSending: false,
  streamingContent: '',
  availableModels: [],

  // Actions
  setSessions: (sessions) => set({ sessions }),

  setActiveChat: (chatId) => {
    storeActiveChatId(chatId)
    set({ activeChatId: chatId, messages: [] })
  },

  setMessages: (messages) => set({ messages }),

  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),

  setStreamingContent: (content) => set({ streamingContent: content }),

  appendStreamingContent: (chunk) => set((state) => ({
    streamingContent: state.streamingContent + chunk
  })),

  clearStreamingContent: () => set({ streamingContent: '' }),

  setIsLoading: (loading) => set({ isLoading: loading }),

  setIsSending: (sending) => set({ isSending: sending }),

  setAvailableModels: (models) => set({ availableModels: models }),

  // Helpers
  getActiveSession: () => {
    const { sessions, activeChatId } = get()
    return sessions.find(s => s.id === activeChatId) || null
  }
}))
