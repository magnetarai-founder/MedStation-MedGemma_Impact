/**
 * Docs & Sheets API Client
 *
 * Handles communication with the backend docs service
 * Implements Notion-style periodic sync
 */

import type { Document } from '@/stores/docsStore'

const API_BASE = '/api/v1/docs'

export interface SyncRequest {
  documents: Partial<Document>[]
  last_sync?: string
}

export interface SyncResponse {
  updated_documents: Document[]
  conflicts: Array<{
    id: string
    server_updated: string
    client_updated: string
    resolution: string
  }>
  sync_timestamp: string
}

export const docsApi = {
  /**
   * Create a new document
   */
  async createDocument(doc: {
    type: 'doc' | 'sheet' | 'insight'
    title: string
    content: any
    is_private?: boolean
    security_level?: string
  }): Promise<Document> {
    const response = await fetch(`${API_BASE}/documents`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(doc),
    })

    if (!response.ok) {
      throw new Error(`Failed to create document: ${response.statusText}`)
    }

    return response.json()
  },

  /**
   * List all documents
   */
  async listDocuments(since?: string): Promise<Document[]> {
    const url = since ? `${API_BASE}/documents?since=${encodeURIComponent(since)}` : `${API_BASE}/documents`

    const response = await fetch(url)

    if (!response.ok) {
      throw new Error(`Failed to list documents: ${response.statusText}`)
    }

    return response.json()
  },

  /**
   * Get a specific document
   */
  async getDocument(id: string): Promise<Document> {
    const response = await fetch(`${API_BASE}/documents/${id}`)

    if (!response.ok) {
      throw new Error(`Failed to get document: ${response.statusText}`)
    }

    return response.json()
  },

  /**
   * Update a document (partial update)
   */
  async updateDocument(
    id: string,
    updates: Partial<Document>
  ): Promise<Document> {
    const response = await fetch(`${API_BASE}/documents/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    })

    if (!response.ok) {
      throw new Error(`Failed to update document: ${response.statusText}`)
    }

    return response.json()
  },

  /**
   * Delete a document
   */
  async deleteDocument(id: string): Promise<void> {
    const response = await fetch(`${API_BASE}/documents/${id}`, {
      method: 'DELETE',
    })

    if (!response.ok) {
      throw new Error(`Failed to delete document: ${response.statusText}`)
    }
  },

  /**
   * Batch sync - Notion-style periodic sync
   * Sends all local changes and receives server updates
   */
  async sync(request: SyncRequest): Promise<SyncResponse> {
    const response = await fetch(`${API_BASE}/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      throw new Error(`Sync failed: ${response.statusText}`)
    }

    return response.json()
  },
}
