/**
 * Docs & Sheets Store
 *
 * Foundation must be solid.
 * "The Lord is my rock, my firm foundation." - Psalm 18:2
 *
 * This foundation supports the Team workspace, collaborative documents,
 * and Insights Lab - built on the Rock that never fails.
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type DocumentType = 'doc' | 'sheet' | 'insight'

export interface Document {
  id: string
  type: DocumentType
  title: string
  content: any // Will be JSON for different document types
  created_at: string
  updated_at: string
  created_by: string

  // Security settings (for Insights)
  is_private?: boolean
  security_level?: 'standard' | 'encrypted' | 'secure_enclave' | 'stealth'
  is_locked?: boolean

  // Collaboration
  shared_with?: string[]
  last_synced?: string
}

export interface SecuritySettings {
  // Auto-lock settings
  lock_on_exit: boolean
  inactivity_lock: 'instant' | '30s' | '1m' | '2m' | '3m' | '4m' | '5m'

  // Privacy settings
  disable_screenshots: boolean
  decoy_mode_enabled: boolean
  stealth_labels: boolean

  // Authentication
  require_touch_id: boolean
}

interface DocsStore {
  // Current workspace view
  workspaceView: 'chat' | 'docs'
  setWorkspaceView: (view: 'chat' | 'docs') => void

  // Documents
  documents: Document[]
  activeDocumentId: string | null
  setActiveDocument: (id: string | null) => void

  // Document CRUD
  createDocument: (type: DocumentType, title?: string) => Document
  updateDocument: (id: string, updates: Partial<Document>) => void
  deleteDocument: (id: string) => void

  // Security
  securitySettings: SecuritySettings
  updateSecuritySettings: (updates: Partial<SecuritySettings>) => void

  // Lock/Unlock
  lockedDocuments: Set<string>
  lockDocument: (id: string) => void
  unlockDocument: (id: string) => void
  lockAllInsights: () => void

  // Last activity (for inactivity detection)
  lastActivity: number
  updateActivity: () => void
}

const defaultSecuritySettings: SecuritySettings = {
  lock_on_exit: true,
  inactivity_lock: '5m',
  disable_screenshots: true,
  decoy_mode_enabled: false,
  stealth_labels: false,
  require_touch_id: true,
}

export const useDocsStore = create<DocsStore>()(
  persist(
    (set, get) => ({
      workspaceView: 'chat',
      setWorkspaceView: (view) => set({ workspaceView: view }),

      documents: [],
      activeDocumentId: null,
      setActiveDocument: (id) => set({ activeDocumentId: id }),

      createDocument: (type, title) => {
        const newDoc: Document = {
          id: `doc_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          type,
          title: title || `New ${type === 'doc' ? 'Document' : type === 'sheet' ? 'Spreadsheet' : 'Insight'}`,
          content: type === 'sheet' ? { rows: [], columns: [] } : type === 'insight' ? { raw: '', analysis: null } : '',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          created_by: 'local_user', // TODO: Replace with actual user ID

          // Security defaults for Insights
          is_private: type === 'insight',
          security_level: type === 'insight' ? 'standard' : undefined,
          is_locked: false,
          shared_with: [],
        }

        set((state) => ({
          documents: [...state.documents, newDoc],
          activeDocumentId: newDoc.id,
        }))

        return newDoc
      },

      updateDocument: (id, updates) => {
        set((state) => ({
          documents: state.documents.map((doc) =>
            doc.id === id
              ? { ...doc, ...updates, updated_at: new Date().toISOString() }
              : doc
          ),
        }))
      },

      deleteDocument: (id) => {
        set((state) => ({
          documents: state.documents.filter((doc) => doc.id !== id),
          activeDocumentId: state.activeDocumentId === id ? null : state.activeDocumentId,
        }))
      },

      securitySettings: defaultSecuritySettings,
      updateSecuritySettings: (updates) => {
        set((state) => ({
          securitySettings: { ...state.securitySettings, ...updates },
        }))
      },

      lockedDocuments: new Set(),
      lockDocument: (id) => {
        set((state) => {
          const newLocked = new Set(state.lockedDocuments)
          newLocked.add(id)
          return { lockedDocuments: newLocked }
        })
      },
      unlockDocument: (id) => {
        set((state) => {
          const newLocked = new Set(state.lockedDocuments)
          newLocked.delete(id)
          return { lockedDocuments: newLocked }
        })
      },
      lockAllInsights: () => {
        set((state) => {
          const insightIds = state.documents
            .filter((doc) => doc.type === 'insight')
            .map((doc) => doc.id)
          return { lockedDocuments: new Set(insightIds) }
        })
      },

      lastActivity: Date.now(),
      updateActivity: () => set({ lastActivity: Date.now() }),
    }),
    {
      name: 'omnistudio.docs',
      // Don't persist locked state or last activity
      partialize: (state) => ({
        workspaceView: state.workspaceView,
        documents: state.documents,
        activeDocumentId: state.activeDocumentId,
        securitySettings: state.securitySettings,
      }),
    }
  )
)
