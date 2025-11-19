/**
 * ProjectLibraryModal Types
 *
 * Shared type definitions for the ProjectLibraryModal module
 */

export interface ProjectDocument {
  id: number
  name: string
  content: string
  tags: string[]
  file_type: 'markdown' | 'text'
  created_at: string
  updated_at: string
}
