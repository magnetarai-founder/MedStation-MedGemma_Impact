/**
 * MagnetarCode Bridge Client
 *
 * Client for calling MagnetarCode's bridge API from MagnetarStudio.
 * Allows delegating code-related tasks to the standalone MagnetarCode service.
 *
 * Configuration:
 * - VITE_MAGNETAR_CODE_API_URL: MagnetarCode API base URL (default: http://localhost:8001)
 * - VITE_MAGNETAR_CODE_API_TOKEN: Shared secret token for authentication
 * - VITE_MAGNETAR_CODE_BRIDGE_ENABLED: Enable/disable bridge (default: false)
 */

// ===== Types =====

export interface AgentRunRequest {
  repo_path: string
  instructions: string
  file?: string
  mode?: 'code_review' | 'test' | 'doc' | 'refactor'
}

export interface AgentRunResponse {
  id: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  created_at: string
}

export interface AgentStatusResponse {
  id: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  result?: {
    files_modified?: string[]
    summary?: string
    mode?: string
  }
  error?: string
  created_at: string
  completed_at?: string
}

export interface BridgeHealthResponse {
  status: string
  bridge_enabled: boolean
  active_runs: number
}

// ===== Configuration =====

const MAGNETAR_CODE_BASE_URL =
  import.meta.env.VITE_MAGNETAR_CODE_API_URL || 'http://localhost:8001'
const MAGNETAR_CODE_API_TOKEN = import.meta.env.VITE_MAGNETAR_CODE_API_TOKEN || ''
const BRIDGE_ENABLED =
  import.meta.env.VITE_MAGNETAR_CODE_BRIDGE_ENABLED === 'true'

// ===== Bridge Client =====

export class MagnetarCodeBridge {
  private baseURL: string
  private token: string
  private enabled: boolean

  constructor(
    baseURL: string = MAGNETAR_CODE_BASE_URL,
    token: string = MAGNETAR_CODE_API_TOKEN,
    enabled: boolean = BRIDGE_ENABLED
  ) {
    this.baseURL = baseURL
    this.token = token
    this.enabled = enabled
  }

  /**
   * Check if bridge is enabled and configured
   */
  isEnabled(): boolean {
    return this.enabled && !!this.token
  }

  /**
   * Run an agent task in MagnetarCode
   */
  async runAgent(request: AgentRunRequest): Promise<AgentRunResponse> {
    if (!this.isEnabled()) {
      throw new Error('MagnetarCode bridge is not enabled')
    }

    const response = await fetch(`${this.baseURL}/bridge/agent/run`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${this.token}`,
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(`MagnetarCode bridge error: ${error.detail || response.statusText}`)
    }

    return response.json()
  }

  /**
   * Get agent run status
   */
  async getAgentStatus(runId: string): Promise<AgentStatusResponse> {
    if (!this.isEnabled()) {
      throw new Error('MagnetarCode bridge is not enabled')
    }

    const response = await fetch(`${this.baseURL}/bridge/agent/status?id=${runId}`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${this.token}`,
      },
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(`MagnetarCode bridge error: ${error.detail || response.statusText}`)
    }

    return response.json()
  }

  /**
   * Poll agent status until completed or failed
   */
  async waitForCompletion(
    runId: string,
    pollInterval: number = 1000,
    maxWaitTime: number = 300000 // 5 minutes
  ): Promise<AgentStatusResponse> {
    const startTime = Date.now()

    while (true) {
      const status = await this.getAgentStatus(runId)

      if (status.status === 'completed' || status.status === 'failed') {
        return status
      }

      if (Date.now() - startTime > maxWaitTime) {
        throw new Error(`Agent run ${runId} timed out after ${maxWaitTime}ms`)
      }

      await new Promise((resolve) => setTimeout(resolve, pollInterval))
    }
  }

  /**
   * Check bridge health (no auth required)
   */
  async checkHealth(): Promise<BridgeHealthResponse> {
    const response = await fetch(`${this.baseURL}/bridge/health`, {
      method: 'GET',
    })

    if (!response.ok) {
      throw new Error(`Health check failed: ${response.statusText}`)
    }

    return response.json()
  }
}

// ===== Singleton Instance =====

let bridgeInstance: MagnetarCodeBridge | null = null

/**
 * Get singleton instance of MagnetarCode bridge client
 */
export function getMagnetarCodeBridge(): MagnetarCodeBridge {
  if (!bridgeInstance) {
    bridgeInstance = new MagnetarCodeBridge()
  }
  return bridgeInstance
}

// ===== Helper Functions =====

/**
 * Quick helper: run agent and wait for completion
 */
export async function runAgentTask(
  request: AgentRunRequest
): Promise<AgentStatusResponse> {
  const bridge = getMagnetarCodeBridge()
  const run = await bridge.runAgent(request)
  return bridge.waitForCompletion(run.id)
}

/**
 * Check if MagnetarCode bridge is available and healthy
 */
export async function isMagnetarCodeAvailable(): Promise<boolean> {
  try {
    const bridge = getMagnetarCodeBridge()
    if (!bridge.isEnabled()) {
      return false
    }
    const health = await bridge.checkHealth()
    return health.status === 'healthy' && health.bridge_enabled
  } catch {
    return false
  }
}
