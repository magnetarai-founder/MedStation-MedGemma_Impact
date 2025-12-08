/**
 * Settings and Library API Client
 */

import { api } from './api'

export interface AppSettings {
  // Performance & Memory
  max_file_size_mb: number
  enable_chunked_processing: boolean
  chunk_size_rows: number
  app_memory_percent: number
  processing_memory_percent: number
  cache_memory_percent: number

  // Default Download Options
  sql_default_format: string
  json_default_format: string
  json_auto_safe: boolean
  json_max_depth: number
  json_flatten_arrays: boolean
  json_preserve_nulls: boolean

  // Naming Patterns
  naming_pattern_global: string
  naming_pattern_sql_excel?: string | null
  naming_pattern_sql_csv?: string | null
  naming_pattern_sql_tsv?: string | null
  naming_pattern_sql_parquet?: string | null
  naming_pattern_sql_json?: string | null
  naming_pattern_json_excel?: string | null
  naming_pattern_json_csv?: string | null
  naming_pattern_json_tsv?: string | null
  naming_pattern_json_parquet?: string | null

  // Automation & Workflows
  automation_enabled: boolean
  auto_save_interval_seconds: number
  auto_backup_enabled: boolean
  workflow_execution_enabled: boolean

  // Database Performance
  database_cache_size_mb: number
  max_query_timeout_seconds: number
  enable_query_optimization: boolean

  // Power User Features
  enable_semantic_search: boolean
  semantic_similarity_threshold: number
  show_keyboard_shortcuts: boolean
  enable_bulk_operations: boolean

  // Session
  session_timeout_hours: number
  clear_temp_on_close: boolean
}

export interface MemoryStatus {
  process_memory_mb: number
  system_total_mb: number
  system_available_mb: number
  system_percent_used: number
  settings: {
    app_percent: number
    processing_percent: number
    cache_percent: number
  }
}

export interface SavedQuery {
  id: number
  name: string
  query: string
  query_type: 'sql' | 'json'
  folder?: string
  description?: string
  tags?: string[]
  created_at: string
  last_used?: string
}

export async function getSettings(): Promise<AppSettings> {
  const response = await fetch('/api/settings')
  if (!response.ok) throw new Error('Failed to fetch settings')
  return response.json()
}

export async function updateSettings(settings: AppSettings): Promise<void> {
  const response = await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  })
  if (!response.ok) throw new Error('Failed to update settings')
}

export async function getMemoryStatus(): Promise<MemoryStatus> {
  const response = await fetch('/api/settings/memory-status')
  if (!response.ok) throw new Error('Failed to fetch memory status')
  return response.json()
}

export async function getSavedQueries(params?: {
  folder?: string
  query_type?: 'sql' | 'json'
}): Promise<SavedQuery[]> {
  const searchParams = new URLSearchParams()
  if (params?.folder) searchParams.append('folder', params.folder)
  if (params?.query_type) searchParams.append('query_type', params.query_type)

  const response = await fetch(
    `/api/saved-queries?${searchParams}`
  )
  if (!response.ok) throw new Error('Failed to fetch saved queries')
  const data = await response.json()
  return data.queries
}

export async function saveQuery(query: {
  name: string
  query: string
  query_type: 'sql' | 'json'
  folder?: string
  description?: string
  tags?: string[]
}): Promise<number> {
  const response = await fetch('/api/saved-queries', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(query),
  })
  if (!response.ok) throw new Error('Failed to save query')
  const data = await response.json()
  return data.id
}

export async function updateQuery(
  id: number,
  updates: Partial<Omit<SavedQuery, 'id' | 'created_at' | 'last_used'>>
): Promise<void> {
  const response = await fetch(`/api/saved-queries/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  })
  if (!response.ok) throw new Error('Failed to update query')
}

export async function deleteQuery(id: number): Promise<void> {
  const response = await fetch(`/api/saved-queries/${id}`, {
    method: 'DELETE',
  })
  if (!response.ok) throw new Error('Failed to delete query')
}
