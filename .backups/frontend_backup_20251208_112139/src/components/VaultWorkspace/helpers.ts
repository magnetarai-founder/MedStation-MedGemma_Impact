/**
 * VaultWorkspace Helper Functions
 * Pure utility functions for formatting and icons
 */

import { FileText, Table2, Lightbulb, Image, Video, Music, FileArchive, Code, FileJson, File } from 'lucide-react'
import type { DocumentType } from '@/stores/docsStore'
import type { LucideIcon } from 'lucide-react'

/**
 * Format bytes to human-readable size
 */
export const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

/**
 * Format date to relative time
 */
export const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}

/**
 * Get icon component for file based on MIME type
 */
export const getFileIcon = (mimeType: string): LucideIcon => {
  if (mimeType.startsWith('image/')) return Image
  if (mimeType.startsWith('video/')) return Video
  if (mimeType.startsWith('audio/')) return Music
  if (mimeType === 'application/pdf') return FileText
  if (mimeType === 'application/json' || mimeType.includes('json')) return FileJson
  if (mimeType.includes('zip') || mimeType.includes('archive') || mimeType.includes('compressed')) return FileArchive
  if (mimeType.includes('text') || mimeType.includes('code') || mimeType.includes('javascript') || mimeType.includes('python')) return Code
  if (mimeType.includes('word') || mimeType.includes('document')) return FileText
  if (mimeType.includes('sheet') || mimeType.includes('excel')) return Table2
  return File
}

/**
 * Get color classes for file icon based on MIME type
 */
export const getFileIconColor = (mimeType: string): string => {
  if (mimeType.startsWith('image/')) return 'text-purple-600 dark:text-purple-400 bg-purple-100 dark:bg-purple-900/30'
  if (mimeType.startsWith('video/')) return 'text-pink-600 dark:text-pink-400 bg-pink-100 dark:bg-pink-900/30'
  if (mimeType.startsWith('audio/')) return 'text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/30'
  if (mimeType === 'application/pdf') return 'text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30'
  if (mimeType.includes('zip') || mimeType.includes('archive')) return 'text-yellow-600 dark:text-yellow-400 bg-yellow-100 dark:bg-yellow-900/30'
  if (mimeType.includes('code') || mimeType.includes('javascript') || mimeType.includes('python')) return 'text-indigo-600 dark:text-indigo-400 bg-indigo-100 dark:bg-indigo-900/30'
  return 'text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-800'
}

/**
 * Get icon component for document type
 */
export const getDocumentIcon = (type: DocumentType): LucideIcon => {
  switch (type) {
    case 'doc':
      return FileText
    case 'sheet':
      return Table2
    case 'insight':
      return Lightbulb
    default:
      return FileText
  }
}

/**
 * Get display title for document (respecting stealth labels)
 */
export const getDisplayTitle = (doc: any, stealthLabelsEnabled: boolean): string => {
  if (stealthLabelsEnabled && doc.stealth_label) {
    return doc.stealth_label
  }
  return doc.title
}

/**
 * Generate breadcrumb navigation from path
 */
export const getBreadcrumbs = (currentPath: string): Array<{ name: string; path: string }> => {
  if (currentPath === '/') return [{ name: 'Root', path: '/' }]

  const parts = currentPath.split('/').filter(Boolean)
  const breadcrumbs = [{ name: 'Root', path: '/' }]

  parts.forEach((part, index) => {
    const path = '/' + parts.slice(0, index + 1).join('/')
    breadcrumbs.push({ name: part, path })
  })

  return breadcrumbs
}

/**
 * Get parent path from current path
 */
export const getParentPath = (currentPath: string): string => {
  if (currentPath === '/') return '/'

  const parts = currentPath.split('/').filter(Boolean)
  parts.pop()
  return parts.length > 0 ? '/' + parts.join('/') : '/'
}

/**
 * Estimate document file size from content
 */
export const estimateDocumentSize = (doc: any): string => {
  const contentSize = JSON.stringify(doc.content).length
  if (contentSize < 1024) return `${contentSize}B`
  if (contentSize < 1024 * 1024) return `${(contentSize / 1024).toFixed(1)}KB`
  return `${(contentSize / (1024 * 1024)).toFixed(1)}MB`
}

/**
 * Check if file is previewable
 */
export const isPreviewable = (mimeType: string): boolean => {
  return (
    mimeType.startsWith('image/') ||
    mimeType.startsWith('text/') ||
    mimeType.startsWith('audio/') ||
    mimeType.startsWith('video/') ||
    mimeType === 'application/pdf' ||
    mimeType === 'application/json'
  )
}

/**
 * Generate random UUID (for upload IDs)
 */
export const generateUUID = (): string => {
  return crypto.randomUUID()
}

/**
 * Sort files by given field and direction
 */
export const sortFiles = (
  files: Array<{ filename: string; created_at: string; file_size: number; mime_type: string }>,
  sortField: 'name' | 'date' | 'size' | 'type',
  sortDirection: 'asc' | 'desc'
): typeof files => {
  return [...files].sort((a, b) => {
    let comparison = 0

    switch (sortField) {
      case 'name':
        comparison = a.filename.localeCompare(b.filename)
        break
      case 'date':
        comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        break
      case 'size':
        comparison = a.file_size - b.file_size
        break
      case 'type':
        comparison = a.mime_type.localeCompare(b.mime_type)
        break
    }

    return sortDirection === 'asc' ? comparison : -comparison
  })
}
