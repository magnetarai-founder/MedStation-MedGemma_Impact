/**
 * Agent Sessions Store (Phase C)
 * Manages state for stateful workspace sessions
 */

import { createWithEqualityFn } from 'zustand/traditional'
import type { AgentSession, AgentSessionCreateRequest } from '@/types/agentSession'
import * as agentSessionsApi from '@/lib/agentSessionsApi'

interface AgentSessionsState {
  // State
  sessions: AgentSession[]
  activeSessionId: string | null
  isLoading: boolean
  error: string | null

  // Derived
  activeSession: () => AgentSession | null
  activeSessions: () => AgentSession[]
  archivedSessions: () => AgentSession[]

  // Actions
  loadSessions: (activeOnly?: boolean) => Promise<void>
  createSession: (request: AgentSessionCreateRequest, setAsActive?: boolean) => Promise<AgentSession | null>
  setActiveSession: (id: string | null) => void
  closeSession: (id: string) => Promise<void>
  refreshSession: (id: string) => Promise<void>
  clearError: () => void
}

export const useAgentSessionsStore = createWithEqualityFn<AgentSessionsState>((set, get) => ({
  // Initial state
  sessions: [],
  activeSessionId: null,
  isLoading: false,
  error: null,

  // Derived state
  activeSession: () => {
    const { sessions, activeSessionId } = get()
    if (!activeSessionId) return null
    return sessions.find(s => s.id === activeSessionId) || null
  },

  activeSessions: () => {
    return get().sessions.filter(s => s.status === 'active')
  },

  archivedSessions: () => {
    return get().sessions.filter(s => s.status === 'archived')
  },

  // Load all sessions for current user
  loadSessions: async (activeOnly = false) => {
    set({ isLoading: true, error: null })
    try {
      const sessions = await agentSessionsApi.listAgentSessions(activeOnly)
      set({ sessions, isLoading: false })
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || error.message || 'Failed to load sessions',
        isLoading: false
      })
    }
  },

  // Create a new session
  createSession: async (request, setAsActive = true) => {
    set({ isLoading: true, error: null })
    try {
      const session = await agentSessionsApi.createAgentSession(request)

      // Add to sessions list
      set(state => ({
        sessions: [session, ...state.sessions],
        activeSessionId: setAsActive ? session.id : state.activeSessionId,
        isLoading: false
      }))

      return session
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || error.message || 'Failed to create session',
        isLoading: false
      })
      return null
    }
  },

  // Set the active session
  setActiveSession: (id) => {
    const { sessions } = get()

    // Validate session exists and is active
    if (id !== null) {
      const session = sessions.find(s => s.id === id)
      if (!session) {
        console.warn(`Session ${id} not found`)
        return
      }
      if (session.status !== 'active') {
        console.warn(`Session ${id} is not active (status: ${session.status})`)
      }
    }

    set({ activeSessionId: id })
  },

  // Close (archive) a session
  closeSession: async (id) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await agentSessionsApi.closeAgentSession(id)

      // Update in sessions list
      set(state => ({
        sessions: state.sessions.map(s => s.id === id ? updated : s),
        // Clear active if closing the active session
        activeSessionId: state.activeSessionId === id ? null : state.activeSessionId,
        isLoading: false
      }))
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || error.message || 'Failed to close session',
        isLoading: false
      })
    }
  },

  // Refresh a specific session (useful after plan updates)
  refreshSession: async (id) => {
    try {
      const session = await agentSessionsApi.getAgentSession(id)

      set(state => ({
        sessions: state.sessions.map(s => s.id === id ? session : s)
      }))
    } catch (error: any) {
      console.error(`Failed to refresh session ${id}:`, error)
      // Don't set global error for refresh failures
    }
  },

  // Clear error message
  clearError: () => set({ error: null }),
}))
