/**
 * Agent Sessions API Client (Phase C)
 * Manages stateful workspace sessions for agent operations
 */

import axios from 'axios'
import type { AgentSession, AgentSessionCreateRequest } from '@/types/agentSession'

const BASE_URL = '/api'

// Create axios instance with same config as main API
const client = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

// Add request interceptor to attach JWT token (same pattern as main API)
client.interceptors.request.use(
  config => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)

// Add response interceptor for error handling
client.interceptors.response.use(
  response => response,
  error => {
    // Log errors but don't block the UI
    console.error('Agent Sessions API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

/**
 * List all agent sessions for the current user
 * @param activeOnly - If true, only return active sessions
 * @returns List of agent sessions, ordered by last_activity_at DESC
 */
export async function listAgentSessions(activeOnly: boolean = false): Promise<AgentSession[]> {
  try {
    const { data } = await client.get<AgentSession[]>('/v1/agent/sessions', {
      params: { active_only: activeOnly }
    })
    return data
  } catch (error) {
    console.error('Failed to list agent sessions:', error)
    throw error
  }
}

/**
 * Get a specific agent session by ID
 * @param sessionId - Session identifier
 * @returns Agent session object
 */
export async function getAgentSession(sessionId: string): Promise<AgentSession> {
  try {
    const { data } = await client.get<AgentSession>(`/v1/agent/sessions/${sessionId}`)
    return data
  } catch (error) {
    console.error(`Failed to get agent session ${sessionId}:`, error)
    throw error
  }
}

/**
 * Create a new agent session
 * @param request - Session creation request with repo_root and optional work_item
 * @returns Created agent session
 */
export async function createAgentSession(
  request: AgentSessionCreateRequest
): Promise<AgentSession> {
  try {
    const { data } = await client.post<AgentSession>('/v1/agent/sessions', request)
    return data
  } catch (error) {
    console.error('Failed to create agent session:', error)
    throw error
  }
}

/**
 * Close (archive) an agent session
 * @param sessionId - Session identifier
 * @returns Updated agent session with status='archived'
 */
export async function closeAgentSession(sessionId: string): Promise<AgentSession> {
  try {
    const { data} = await client.post<AgentSession>(`/v1/agent/sessions/${sessionId}/close`)
    return data
  } catch (error) {
    console.error(`Failed to close agent session ${sessionId}:`, error)
    throw error
  }
}
