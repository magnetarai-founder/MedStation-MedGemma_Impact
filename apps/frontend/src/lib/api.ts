import axios from 'axios'
import { useLogsStore } from '@/stores/logsStore'

const BASE_URL = '/api'

export interface SessionResponse {
  session_id: string
  created_at: string
}

export interface FileUploadResponse {
  filename: string
  size_mb: number
  row_count: number
  column_count: number
  columns: Array<{
    original_name: string
    clean_name: string
    dtype: string
    non_null_count: number
    null_count: number
  }>
  preview: Record<string, any>[]
}

export interface QueryResponse {
  query_id: string
  row_count: number
  column_count: number
  columns: string[]
  execution_time_ms: number
  preview: Record<string, any>[]
  has_more: boolean
}

export interface ValidationResponse {
  is_valid: boolean
  errors: string[]
  warnings: string[]
}

// Helper to parse and format SQL errors
const formatSQLError = (errorMessage: string): string => {
  // Extract the main error type and message
  const errorParts = errorMessage.split(':').map(s => s.trim())

  // Look for specific error patterns
  if (errorMessage.includes('Referenced column') && errorMessage.includes('not found')) {
    const columnMatch = errorMessage.match(/Referenced column "([^"]+)" not found/)
    const columnName = columnMatch ? columnMatch[1] : 'unknown'

    // Extract candidate bindings if available
    let candidates = ''
    const candidateMatch = errorMessage.match(/Candidate bindings: (.+?)(?:LINE|$)/s)
    if (candidateMatch) {
      candidates = candidateMatch[1].trim()
    }

    return `❌ Column "${columnName}" not found\n\n💡 Available columns: ${candidates || 'Check the Columns panel'}\n\n⚠️ Remember: Column names are case-sensitive!`
  }

  if (errorMessage.includes('Binder Error')) {
    const mainError = errorParts[errorParts.length - 1] || errorMessage
    return `❌ SQL Error: ${mainError}\n\n💡 Tip: Check column names in the Columns panel. Use double quotes for names with spaces.`
  }

  if (errorMessage.includes('Parser Error')) {
    return `❌ SQL Syntax Error\n\n${errorMessage.split('Parser Error:')[1] || errorMessage}\n\n💡 Check your SQL syntax for typos or missing keywords.`
  }

  if (errorMessage.includes('Catalog Error')) {
    const tableMatch = errorMessage.match(/Table with name ([^\s]+) does not exist/)
    if (tableMatch) {
      return `❌ Table "${tableMatch[1]}" not found\n\n💡 Use "excel_file" as your table name after uploading a file.`
    }
  }

  // Fallback: clean up the error message
  return errorMessage
    .replace(/API Error:\s*/g, '')
    .replace(/Column Error:\s*/g, '')
    .replace(/Binder Error:\s*/g, '')
    .replace(/Parser Error:\s*/g, '')
    .replace(/Catalog Error:\s*/g, '')
    .replace(/LINE \d+:.*\^/s, '')
    .trim()
}

// Helper to emit log events
let logIdCounter = 0
const emitLog = (level: 'info' | 'warning' | 'error' | 'success', message: string) => {
  const entry = {
    id: `${Date.now()}-${logIdCounter++}`,
    timestamp: new Date().toLocaleTimeString(),
    level,
    message,
  }
  // Fire event for any listeners
  try { window.dispatchEvent(new CustomEvent('app-log', { detail: entry })) } catch {}
  // Persist in store so Logs panel can show past entries
  try { useLogsStore.getState().appendLog(entry) } catch {}
}

class NeutronAPI {
  public readonly BASE_URL = BASE_URL

  private client = axios.create({
    baseURL: BASE_URL,
    headers: {
      'Content-Type': 'application/json',
    },
    timeout: 300000, // 5 minutes timeout for large files
  })

  constructor() {
    // Add request interceptor to attach JWT token
    this.client.interceptors.request.use(
      config => {
        const token = localStorage.getItem('auth_token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      error => Promise.reject(error)
    )

    // Add response interceptor for better error handling
    this.client.interceptors.response.use(
      response => response,
      error => {
        if (error.response) {
          // Server responded with error
          const errorDetail = error.response.data?.detail || error.message
          const formattedError = formatSQLError(errorDetail)
          emitLog('error', formattedError)
          try { window.dispatchEvent(new CustomEvent('open-logs')) } catch {}
        } else if (error.request) {
          // No response received
          emitLog('error', '❌ Server not responding\n\n💡 Make sure the backend is running (port 8000)')
          try { window.dispatchEvent(new CustomEvent('open-logs')) } catch {}
        } else {
          // Request setup error
          emitLog('error', `❌ Request error: ${error.message}`)
          try { window.dispatchEvent(new CustomEvent('open-logs')) } catch {}
        }
        return Promise.reject(error)
      }
    )
  }

  // Generic HTTP methods for flexible API calls
  async get(url: string, config?: any) {
    return this.client.get(url, config)
  }

  async post(url: string, data?: any, config?: any) {
    return this.client.post(url, data, config)
  }

  async put(url: string, data?: any, config?: any) {
    return this.client.put(url, data, config)
  }

  async delete(url: string, config?: any) {
    return this.client.delete(url, config)
  }

  async createSession(): Promise<SessionResponse> {
    const maxRetries = 5
    let lastError: any
    
    for (let i = 0; i < maxRetries; i++) {
      try {
        const { data } = await this.client.post('/sessions/create')
        return data
      } catch (error: any) {
        lastError = error
        if (error.code === 'ECONNREFUSED' && i < maxRetries - 1) {
          // Backend not ready yet, wait and retry
          await new Promise(resolve => setTimeout(resolve, 2000))
          continue
        }
        throw error
      }
    }
    
    throw lastError
  }

  async deleteSession(sessionId: string): Promise<void> {
    await this.client.delete(`/sessions/${sessionId}`)
  }

  async uploadFile(sessionId: string, file: File): Promise<FileUploadResponse> {
    emitLog('info', `Uploading file: ${file.name}`)
    const formData = new FormData()
    formData.append('file', file)

    const { data } = await this.client.post(
      `/sessions/${sessionId}/upload`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    )
    emitLog('success', `File loaded: ${data.row_count} rows, ${data.column_count} columns`)
    return data
  }

  async validateSQL(sessionId: string, sql: string): Promise<ValidationResponse> {
    const { data } = await this.client.post(`/sessions/${sessionId}/validate`, { sql })
    return data
  }

  async executeQuery(
    sessionId: string,
    sql: string,
    options?: {
      limit?: number | null
      dialect?: string
      timeout_seconds?: number
      signal?: AbortSignal
    }
  ): Promise<QueryResponse> {
    const queryType = options?.limit === 10 ? 'Preview query' : 'Query'
    emitLog('info', `Executing ${queryType}...`)

    const { signal, ...queryOptions } = options || {}

    const { data } = await this.client.post(`/sessions/${sessionId}/query`, {
      sql,
      ...queryOptions,
    }, {
      signal
    })

    emitLog('success', `${queryType} completed: ${data.row_count} rows in ${data.execution_time_ms}ms`)
    return data
  }

  async exportResults(
    sessionId: string,
    queryId: string,
    format: 'excel' | 'csv' | 'parquet' | 'json',
    filename?: string
  ): Promise<Blob> {
    const { data } = await this.client.post(
      `/sessions/${sessionId}/export`,
      {
        query_id: queryId,
        format,
        filename,
      },
      {
        responseType: 'blob',
      }
    )
    return data
  }

  async listTables(sessionId: string): Promise<{
    tables: Array<{
      name: string
      file: string
      row_count: number
      column_count: number
    }>
  }> {
    const { data } = await this.client.get(`/sessions/${sessionId}/tables`)
    return data
  }

  // JSON to Excel endpoints
  async uploadJson(sessionId: string, file: File): Promise<{
    filename: string
    size_mb: number
    object_count: number
    depth: number
    columns: string[]
    preview: Record<string, any>[]
  }> {
    emitLog('info', `Uploading JSON file: ${file.name}`)
    const formData = new FormData()
    formData.append('file', file)

    const { data } = await this.client.post(
      `/sessions/${sessionId}/json/upload`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    )
    emitLog('success', `JSON loaded: ${data.object_count} objects`)
    return data
  }

  async convertJson(
    sessionId: string,
    jsonData: string,
    options?: Record<string, any>,
    signal?: AbortSignal
  ): Promise<{
    success: boolean
    output_file: string
    total_rows: number
    sheets: string[]
    columns: string[]
    preview: Record<string, any>[]
    is_preview_only?: boolean
  }> {
    emitLog('info', 'Converting JSON to Excel...')

    const { data } = await this.client.post(`/sessions/${sessionId}/json/convert`, {
      json_data: jsonData,
      options: options || {}
    }, {
      signal
    })

    emitLog('success', `Conversion completed: ${data.total_rows} rows`)
    return data
  }

  async downloadJsonResult(
    sessionId: string,
    format: 'excel' | 'csv' | 'tsv' | 'parquet'
  ): Promise<Blob> {
    const { data } = await this.client.get(
      `/sessions/${sessionId}/json/download`,
      {
        params: { format },
        responseType: 'blob',
      }
    )
    return data
  }

  // Chat/AI endpoints
  async preloadModel(model: string, keepAlive: string = '1h'): Promise<void> {
    const { data } = await this.client.post(
      `/v1/chat/models/preload?model=${encodeURIComponent(model)}&keep_alive=${encodeURIComponent(keepAlive)}`
    )
    return data
  }

  // Query History endpoints
  async getQueryHistory(sessionId: string): Promise<{
    history: Array<{
      id: string
      query: string
      timestamp: string
      executionTime?: number
      rowCount?: number
      status: 'success' | 'error'
    }>
  }> {
    const { data } = await this.client.get(`/sessions/${sessionId}/query-history`)
    return data
  }

  async deleteQueryFromHistory(sessionId: string, queryId: string): Promise<void> {
    await this.client.delete(`/sessions/${sessionId}/query-history/${queryId}`)
  }

  // Agent Orchestrator endpoints
  async agentRoute(input: string, cwd?: string, repoRoot?: string): Promise<{
    intent: string
    confidence: number
    model_hint?: string
    next_action: string
  }> {
    const { data } = await this.client.post('/v1/agent/route', {
      input,
      cwd,
      repo_root: repoRoot
    })
    return data
  }

  async agentPlan(input: string, contextBundle?: any, model?: string): Promise<{
    steps: Array<{
      description: string
      risk_level: string
      estimated_files: number
    }>
    risks: string[]
    requires_confirmation: boolean
    estimated_time_min: number
    model_used: string
  }> {
    const { data } = await this.client.post('/v1/agent/plan', {
      input,
      context_bundle: contextBundle,
      model
    })
    return data
  }

  async agentContext(params: {
    sessionId?: string
    cwd?: string
    repoRoot?: string
    openFiles?: string[]
  }): Promise<{
    file_tree_slice: string[]
    recent_diffs: any[]
    embeddings_hits: string[]
    chat_snippets: string[]
    active_models: string[]
  }> {
    const { data } = await this.client.post('/v1/agent/context', {
      session_id: params.sessionId,
      cwd: params.cwd,
      repo_root: params.repoRoot,
      open_files: params.openFiles || []
    })
    return data
  }

  async agentApply(params: {
    input: string
    planId?: string
    repoRoot?: string
    model?: string
    dryRun?: boolean
  }): Promise<{
    success: boolean
    patches: Array<{
      path: string
      patch_text: string
      summary: string
    }>
    summary: string
    patch_id?: string
  }> {
    const { data } = await this.client.post('/v1/agent/apply', {
      plan_id: params.planId,
      input: params.input,
      repo_root: params.repoRoot,
      model: params.model,
      dry_run: params.dryRun || false
    })
    return data
  }
}

export const api = new NeutronAPI()

/**
 * Authenticated fetch wrapper that automatically includes JWT token
 * Use this instead of raw fetch() for API calls
 */
export const authFetch = async (url: string, options: RequestInit = {}): Promise<Response> => {
  const token = localStorage.getItem('auth_token')

  const headers = new Headers(options.headers || {})
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  return fetch(url, {
    ...options,
    headers,
  })
}
