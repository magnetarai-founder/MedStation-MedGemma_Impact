import { create } from 'zustand'
import { persist } from 'zustand/middleware'

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

type TonePreset = 'creative' | 'balanced' | 'precise' | 'custom'

// Model classification types
export type ModelClassification =
  | 'chat'       // General conversation
  | 'reasoning'  // Step-by-step logical reasoning
  | 'code'       // Programming and development
  | 'writing'    // Creative writing, documents
  | 'research'   // Research, analysis, summarization
  | 'intelligent' // Auto-detect based on task

// Per-model configuration
export interface ModelConfig {
  classification: ModelClassification
  systemPrompt: string  // Model-specific system prompt

  // Model-specific LLM parameters
  tone: TonePreset
  temperature: number
  topP: number
  topK: number
  repeatPenalty: number
}

interface ChatSettings {
  defaultModel: string
  autoGenerateTitles: boolean
  contextWindow: number

  // Orchestrator Model (always running for Jarvis routing)
  orchestratorModel: string

  // Global LLM Parameters (used when model-specific not set)
  tone: TonePreset
  temperature: number
  topP: number
  topK: number
  repeatPenalty: number
  systemPrompt: string  // Global system prompt

  // Per-model configurations
  modelConfigs: Record<string, ModelConfig>
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

  // Settings
  settings: ChatSettings

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
  updateSettings: (settings: Partial<ChatSettings>) => void
  updateModelConfig: (modelName: string, config: Partial<ModelConfig>) => void
  getModelConfig: (modelName: string) => ModelConfig | null

  // Helpers
  getActiveSession: () => ChatSession | null
}

// Get last active chat from sessionStorage
const getStoredActiveChatId = (): string | null => {
  // Don't restore on fresh app load - always start with no chat selected
  return null
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

export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      // Initial state - try to restore last active chat from session
      sessions: [],
      activeChatId: getStoredActiveChatId(),
      messages: [],
      isLoading: false,
      isSending: false,
      streamingContent: '',
      availableModels: [],

      // Settings with defaults (Balanced preset)
      settings: {
        defaultModel: 'qwen2.5-coder:7b-instruct',
        autoGenerateTitles: true,
        contextWindow: 75,

        // Orchestrator Model (empty by default, user configures)
        orchestratorModel: '',

        // Global LLM Parameters - Balanced preset
        tone: 'balanced',
        temperature: 0.7,
        topP: 0.9,
        topK: 40,
        repeatPenalty: 1.1,
        systemPrompt: '',

        // Per-model configurations
        modelConfigs: {}
      },

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

      updateSettings: (newSettings) => set((state) => {
        let updatedSettings = { ...state.settings, ...newSettings }

        // Apply tone presets
        if (newSettings.tone && newSettings.tone !== 'custom') {
          const presets = {
            creative: {
              temperature: 1.2,
              topP: 0.95,
              topK: 60,
              repeatPenalty: 1.05
            },
            balanced: {
              temperature: 0.7,
              topP: 0.9,
              topK: 40,
              repeatPenalty: 1.1
            },
            precise: {
              temperature: 0.3,
              topP: 0.8,
              topK: 20,
              repeatPenalty: 1.2
            }
          }

          if (newSettings.tone in presets) {
            updatedSettings = {
              ...updatedSettings,
              ...presets[newSettings.tone as keyof typeof presets]
            }
          }
        }

        return { settings: updatedSettings }
      }),

      updateModelConfig: (modelName, configUpdate) => set((state) => {
        const existingConfig = state.settings.modelConfigs[modelName] || {
          classification: 'intelligent',
          systemPrompt: '',
          tone: 'balanced',
          temperature: 0.7,
          topP: 0.9,
          topK: 40,
          repeatPenalty: 1.1
        }

        const updatedConfig = { ...existingConfig, ...configUpdate }

        // Apply tone presets if tone is changed
        if (configUpdate.tone && configUpdate.tone !== 'custom') {
          const presets = {
            creative: {
              temperature: 1.2,
              topP: 0.95,
              topK: 60,
              repeatPenalty: 1.05
            },
            balanced: {
              temperature: 0.7,
              topP: 0.9,
              topK: 40,
              repeatPenalty: 1.1
            },
            precise: {
              temperature: 0.3,
              topP: 0.8,
              topK: 20,
              repeatPenalty: 1.2
            }
          }

          if (configUpdate.tone in presets) {
            Object.assign(updatedConfig, presets[configUpdate.tone as keyof typeof presets])
          }
        }

        return {
          settings: {
            ...state.settings,
            modelConfigs: {
              ...state.settings.modelConfigs,
              [modelName]: updatedConfig
            }
          }
        }
      }),

      getModelConfig: (modelName) => {
        const { settings } = get()
        return settings.modelConfigs[modelName] || null
      },

      // Helpers
      getActiveSession: () => {
        const { sessions, activeChatId } = get()
        return sessions.find(s => s.id === activeChatId) || null
      }
    }),
    {
      name: 'neutron-chat-settings',
      // Only persist settings, not runtime state
      partialize: (state) => ({ settings: state.settings })
    }
  )
)
