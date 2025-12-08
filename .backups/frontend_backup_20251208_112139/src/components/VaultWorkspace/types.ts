/**
 * VaultWorkspace Type Definitions
 */

import type { DocumentType } from '@/stores/docsStore'

export interface VaultFile {
  id: string
  filename: string
  file_size: number
  mime_type: string
  folder_path: string
  created_at: string
}

export interface VaultFolder {
  id: string
  folder_name: string
  folder_path: string
  parent_path: string
  created_at: string
}

export interface FileTag {
  tag_name: string
  tag_color: string
}

export interface UploadProgress {
  id: string
  name: string
  size: number
  progress: number
  status: 'uploading' | 'complete' | 'error'
  error?: string
}

export interface ContextMenuState {
  x: number
  y: number
  type: 'file' | 'folder' | 'document'
  item: any
  docId?: string
}

export interface DeleteTarget {
  type: 'file' | 'folder'
  id?: string
  name: string
  path?: string
}

export interface RenameTarget {
  type: 'file' | 'folder'
  id?: string
  currentName: string
  path?: string
}

export interface MoveTarget {
  id: string
  filename: string
  currentPath: string
}

export interface StealthLabelModal {
  docId: string
  currentLabel: string
}

export interface SearchFilters {
  query: string
  mimeType: string
  tags: string[]
  dateFrom: string
  dateTo: string
  minSize: string
  maxSize: string
  folderPath: string
}

export interface ShareLinkData {
  id: string
  share_token: string
  created_at: string
  expires_at?: string
  max_downloads?: number
  download_count: number
  password_protected: boolean
}

export interface FileVersion {
  id: string
  version_number: number
  file_size: number
  created_at: string
  created_by: string
}

export interface FileComment {
  id: string
  comment_text: string
  created_at: string
  created_by: string
  user_name?: string
}

export interface StorageStats {
  total_files: number
  total_size: number
  used_percentage: number
  file_type_breakdown: Array<{
    mime_type: string
    count: number
    total_size: number
  }>
  folder_sizes: Array<{
    folder_path: string
    file_count: number
    total_size: number
  }>
}

export interface AuditLogEntry {
  id: string
  action: string
  file_id?: string
  filename?: string
  details: string
  created_at: string
  user_name: string
}

export interface RealtimeNotification {
  id: string
  type: string
  message: string
  timestamp: string
}

export interface AnalyticsData {
  storageTrends: {
    labels: string[]
    data: number[]
  } | null
  accessPatterns: {
    labels: string[]
    data: number[]
  } | null
  activityTimeline: Array<{
    date: string
    uploads: number
    downloads: number
    shares: number
  }> | null
}

export type ViewMode = 'grid' | 'list'
export type SortField = 'name' | 'date' | 'size' | 'type'
export type SortDirection = 'asc' | 'desc'
export type FilterType = 'all' | DocumentType

export interface Breadcrumb {
  name: string
  path: string
}

export interface TrashFile {
  id: string
  filename: string
  file_size: number
  mime_type: string
  folder_path: string
  deleted_at: string
  original_path: string
}

export interface ExportOptions {
  format: 'zip' | 'tar'
  includeMetadata: boolean
  selectedFiles?: string[]
}
