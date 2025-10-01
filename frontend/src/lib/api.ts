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

// Helper to emit log events
const emitLog = (level: 'info' | 'warning' | 'error' | 'success', message: string) => {
  const entry = {
    id: Date.now().toString(),
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
    // Add response interceptor for better error handling
    this.client.interceptors.response.use(
      response => response,
      error => {
        if (error.response) {
          // Server responded with error
          emitLog('error', `API Error: ${error.response.data?.detail || error.message}`)
          try { window.dispatchEvent(new CustomEvent('open-logs')) } catch {}
        } else if (error.request) {
          // No response received
          emitLog('error', 'Server not responding. Make sure the backend is running.')
          try { window.dispatchEvent(new CustomEvent('open-logs')) } catch {}
        } else {
          // Request setup error
          emitLog('error', `Request error: ${error.message}`)
          try { window.dispatchEvent(new CustomEvent('open-logs')) } catch {}
        }
        return Promise.reject(error)
      }
    )
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
    }
  ): Promise<QueryResponse> {
    const queryType = options?.limit === 10 ? 'Preview query' : 'Query'
    emitLog('info', `Executing ${queryType}...`)
    
    const { data } = await this.client.post(`/sessions/${sessionId}/query`, {
      sql,
      ...options,
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
    options?: {
      expand_arrays?: boolean
      max_depth?: number
      auto_safe?: boolean
      include_summary?: boolean
    },
    signal?: AbortSignal
  ): Promise<{
    success: boolean
    output_file: string
    total_rows: number
    sheets: string[]
    columns: string[]
    preview: Record<string, any>[]
  }> {
    emitLog('info', 'Converting JSON to Excel...')
    
    const { data } = await this.client.post(`/sessions/${sessionId}/json/convert`, {
      json_data: jsonData,
      options: options || {
        expand_arrays: true,
        max_depth: 5,
        auto_safe: true,
        include_summary: true
      }
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
}

export const api = new NeutronAPI()
