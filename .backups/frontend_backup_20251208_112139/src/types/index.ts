/**
 * Centralized Type Definitions
 * Shared types used across the application
 */

// ============================================================================
// Session & File Types
// ============================================================================

export interface SessionResponse {
  session_id: string
  created_at: string
}

export interface FileUploadResponse {
  filename: string
  original_name?: string
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

// ============================================================================
// Query Types
// ============================================================================

export interface QueryResponse {
  query_id: string
  sql_query?: string
  row_count: number
  column_count: number
  columns: string[]
  execution_time_ms: number
  preview: Record<string, any>[]
  has_more: boolean
  is_preview_only?: boolean
}

export interface ValidationResponse {
  is_valid: boolean
  errors: string[]
  warnings: string[]
}

// ============================================================================
// Model Types
// ============================================================================

export interface ModelStatus {
  name: string
  loaded: boolean
  is_favorite: boolean
  size: string
  modified_at?: string
}

export interface OllamaServerState {
  running: boolean
  loadedModels: string[]
  modelCount: number
}

// ============================================================================
// Chat Types
// ============================================================================

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  model?: string
}

export interface ChatSession {
  id: string
  title: string
  messages: ChatMessage[]
  created_at: number
  updated_at: number
}

export type AssistantMode = 'general' | 'data-analyst' | 'pair-programmer' | 'code-reviewer'

// ============================================================================
// Team Chat / P2P Types
// ============================================================================

export interface Peer {
  peer_id: string
  display_name: string
  device_name: string
  status: 'online' | 'offline'
  last_seen?: string
}

export interface Channel {
  channel_id: string
  name: string
  type: 'public' | 'private' | 'dm'
  members: string[]
  description?: string
  created_at: string
}

export interface TeamMessage {
  message_id: string
  channel_id: string
  sender_id: string
  content: string
  type: 'text' | 'file'
  timestamp: string
  reply_to?: string
}

export interface P2PStatus {
  initialized: boolean
  peer_id?: string
  display_name?: string
  device_name?: string
}

// ============================================================================
// Settings Types
// ============================================================================

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

// ============================================================================
// JSON Conversion Types
// ============================================================================

export interface JsonUploadResponse {
  filename: string
  size_mb: number
  object_count: number
  depth: number
  columns: string[]
  preview: Record<string, any>[]
}

export interface JsonConversionOptions {
  safe_mode?: boolean
  max_depth?: number
  flatten_arrays?: boolean
  custom_mapping?: Record<string, string>
}

export interface JsonConversionResult {
  success: boolean
  output_file: string
  total_rows: number
  sheets: string[]
  columns: string[]
  preview: Record<string, any>[]
  is_preview_only?: boolean
}

// ============================================================================
// Navigation Types
// ============================================================================

export type NavTab = 'team' | 'chat' | 'database' | 'queries'

export type NavItem = 'team' | 'chat' | 'database' | 'queries' | 'json' | 'library'

// ============================================================================
// Error Tracking Types
// ============================================================================

export interface ErrorLog {
  id: string
  timestamp: string
  type: 'error' | 'warning' | 'info'
  message: string
  stack?: string
  context?: Record<string, any>
  userAgent?: string
  url?: string
}

// ============================================================================
// Hot Slot Types (Model Management)
// ============================================================================

export interface HotSlot {
  slotNumber: number
  model: ModelStatus | null
}
