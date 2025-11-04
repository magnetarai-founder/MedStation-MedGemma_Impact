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
import { useUserStore } from './userStore'
import { generateVerificationToken, encryptData, verifyPassphrase } from '../lib/encryption'

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

  // Vault mode (for dual vault storage)
  vaultMode?: 'real' | 'decoy'

  // Stealth label (innocuous cover name when stealth_labels setting is enabled)
  stealth_label?: string

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
  workspaceView: 'chat' | 'docs' | 'workflows' | 'vault'
  setWorkspaceView: (view: 'chat' | 'docs' | 'workflows' | 'vault') => void

  // Documents
  documents: Document[]
  realVaultDocuments: Document[]
  decoyVaultDocuments: Document[]
  activeDocumentId: string | null
  setActiveDocument: (id: string | null) => void

  // Document CRUD
  createDocument: (type: DocumentType, title?: string) => Document
  updateDocument: (id: string, updates: Partial<Document>) => void
  deleteDocument: (id: string) => void

  // Vault document getters
  getVaultDocuments: () => Document[]
  getRealVaultDocuments: () => Document[]
  getDecoyVaultDocuments: () => Document[]

  // Vault document management
  moveToVault: (docId: string, vaultMode: 'real' | 'decoy') => void
  removeFromVault: (docId: string) => void

  // Insights model selection
  selectedInsightModel: string
  setSelectedInsightModel: (model: string) => void

  // Vault
  vaultSetupComplete: boolean
  vaultUnlocked: boolean
  vaultPasswordHash: string | null
  vaultPassword2Hash: string | null  // Second real password (when Touch ID not required)
  decoyPasswordHash: string | null
  currentVaultMode: 'real' | 'decoy' | null

  // Vault encryption (stored encrypted verification tokens)
  realVaultVerification: { encrypted: string; salt: string; iv: string } | null
  realVault2Verification: { encrypted: string; salt: string; iv: string } | null
  decoyVaultVerification: { encrypted: string; salt: string; iv: string } | null

  // Runtime passphrase (NOT persisted, only in memory)
  vaultPassphrase: string | null

  setVaultPasswords: (realPassword: string, decoyPassword: string, realPassword2?: string) => Promise<void>
  unlockVault: (password: string) => Promise<boolean>
  lockVault: () => void

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
      realVaultDocuments: [],
      decoyVaultDocuments: [],
      activeDocumentId: null,
      setActiveDocument: (id) => set({ activeDocumentId: id }),

      selectedInsightModel: '',
      setSelectedInsightModel: (model) => set({ selectedInsightModel: model }),

      // Vault state
      vaultSetupComplete: false,
      vaultUnlocked: false,
      vaultPasswordHash: null,
      vaultPassword2Hash: null,
      decoyPasswordHash: null,
      currentVaultMode: null,
      realVaultVerification: null,
      realVault2Verification: null,
      decoyVaultVerification: null,
      vaultPassphrase: null,

      setVaultPasswords: async (realPassword, decoyPassword, realPassword2) => {
        // Simple hash using Web Crypto API (for backwards compatibility)
        const hashPassword = async (password: string): Promise<string> => {
          const encoder = new TextEncoder()
          const data = encoder.encode(password)
          const hashBuffer = await crypto.subtle.digest('SHA-256', data)
          const hashArray = Array.from(new Uint8Array(hashBuffer))
          return hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
        }

        const realHash = await hashPassword(realPassword)
        const decoyHash = await hashPassword(decoyPassword)

        // Create constant verification tokens for AES-256 encryption
        const VAULT_VERIFICATION_TOKEN = 'ElohimOS_Vault_Verification_Real'
        const VAULT2_VERIFICATION_TOKEN = 'ElohimOS_Vault_Verification_Real2'
        const DECOY_VERIFICATION_TOKEN = 'ElohimOS_Vault_Verification_Decoy'

        // Encrypt the verification tokens
        const realVerification = await encryptData(VAULT_VERIFICATION_TOKEN, realPassword)
        const decoyVerification = await encryptData(DECOY_VERIFICATION_TOKEN, decoyPassword)

        // Handle optional second real password
        let real2Hash: string | null = null
        let real2Verification: { encrypted: string; salt: string; iv: string } | null = null

        if (realPassword2) {
          real2Hash = await hashPassword(realPassword2)
          real2Verification = await encryptData(VAULT2_VERIFICATION_TOKEN, realPassword2)
        }

        set({
          vaultSetupComplete: true,
          vaultPasswordHash: realHash,
          vaultPassword2Hash: real2Hash,
          decoyPasswordHash: decoyHash,
          realVaultVerification: realVerification,
          realVault2Verification: real2Verification,
          decoyVaultVerification: decoyVerification,
        })
      },

      unlockVault: async (password) => {
        const state = get()

        const VAULT_VERIFICATION_TOKEN = 'ElohimOS_Vault_Verification_Real'
        const VAULT2_VERIFICATION_TOKEN = 'ElohimOS_Vault_Verification_Real2'
        const DECOY_VERIFICATION_TOKEN = 'ElohimOS_Vault_Verification_Decoy'

        // Try to verify against real vault using AES encryption
        if (state.realVaultVerification) {
          const { encrypted, salt, iv } = state.realVaultVerification
          const isReal = await verifyPassphrase(
            VAULT_VERIFICATION_TOKEN,
            encrypted,
            salt,
            iv,
            password
          ).catch(() => false)

          if (isReal) {
            set({
              vaultUnlocked: true,
              currentVaultMode: 'real',
              vaultPassphrase: password
            })
            return true
          }
        }

        // Try to verify against second real vault password (if exists)
        if (state.realVault2Verification) {
          const { encrypted, salt, iv } = state.realVault2Verification
          const isReal2 = await verifyPassphrase(
            VAULT2_VERIFICATION_TOKEN,
            encrypted,
            salt,
            iv,
            password
          ).catch(() => false)

          if (isReal2) {
            set({
              vaultUnlocked: true,
              currentVaultMode: 'real',
              vaultPassphrase: password
            })
            return true
          }
        }

        // Try to verify against decoy vault using AES encryption
        if (state.decoyVaultVerification) {
          const { encrypted, salt, iv } = state.decoyVaultVerification
          const isDecoy = await verifyPassphrase(
            DECOY_VERIFICATION_TOKEN,
            encrypted,
            salt,
            iv,
            password
          ).catch(() => false)

          if (isDecoy) {
            set({
              vaultUnlocked: true,
              currentVaultMode: 'decoy',
              vaultPassphrase: password
            })
            return true
          }
        }

        // Fallback to hash-based verification for backwards compatibility
        const encoder = new TextEncoder()
        const data = encoder.encode(password)
        const hashBuffer = await crypto.subtle.digest('SHA-256', data)
        const hashArray = Array.from(new Uint8Array(hashBuffer))
        const enteredHash = hashArray.map(b => b.toString(16).padStart(2, '0')).join('')

        if (enteredHash === state.vaultPasswordHash) {
          set({
            vaultUnlocked: true,
            currentVaultMode: 'real',
            vaultPassphrase: password
          })
          return true
        } else if (enteredHash === state.vaultPassword2Hash) {
          set({
            vaultUnlocked: true,
            currentVaultMode: 'real',
            vaultPassphrase: password
          })
          return true
        } else if (enteredHash === state.decoyPasswordHash) {
          set({
            vaultUnlocked: true,
            currentVaultMode: 'decoy',
            vaultPassphrase: password
          })
          return true
        }

        return false
      },

      lockVault: () => {
        set({ vaultUnlocked: false, currentVaultMode: null, vaultPassphrase: null })
      },

      createDocument: (type, title) => {
        // Get user ID from user store
        const userId = useUserStore.getState().getUserId()
        const state = get()

        const newDoc: Document = {
          id: `doc_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          type,
          title: title || `New ${type === 'doc' ? 'Document' : type === 'sheet' ? 'Spreadsheet' : 'Insight'}`,
          content: type === 'sheet' ? { rows: [], columns: [] } : type === 'insight' ? { raw: '', analysis: null } : '',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          created_by: userId,

          // Security defaults for Insights
          is_private: type === 'insight',
          security_level: type === 'insight' ? 'standard' : undefined,
          is_locked: false,
          shared_with: [],
        }

        // If vault is unlocked and we're in vault view, assign to current vault mode
        if (state.vaultUnlocked && state.currentVaultMode && state.workspaceView === 'vault') {
          newDoc.vaultMode = state.currentVaultMode

          if (state.currentVaultMode === 'real') {
            set((state) => ({
              realVaultDocuments: [...state.realVaultDocuments, newDoc],
              activeDocumentId: newDoc.id,
            }))
          } else {
            set((state) => ({
              decoyVaultDocuments: [...state.decoyVaultDocuments, newDoc],
              activeDocumentId: newDoc.id,
            }))
          }
        } else {
          // Regular document (non-vault)
          set((state) => ({
            documents: [...state.documents, newDoc],
            activeDocumentId: newDoc.id,
          }))
        }

        return newDoc
      },

      updateDocument: (id, updates) => {
        set((state) => {
          // Check which array the document belongs to
          const isInRealVault = state.realVaultDocuments.some(doc => doc.id === id)
          const isInDecoyVault = state.decoyVaultDocuments.some(doc => doc.id === id)

          if (isInRealVault) {
            return {
              realVaultDocuments: state.realVaultDocuments.map((doc) =>
                doc.id === id
                  ? { ...doc, ...updates, updated_at: new Date().toISOString() }
                  : doc
              ),
            }
          } else if (isInDecoyVault) {
            return {
              decoyVaultDocuments: state.decoyVaultDocuments.map((doc) =>
                doc.id === id
                  ? { ...doc, ...updates, updated_at: new Date().toISOString() }
                  : doc
              ),
            }
          } else {
            return {
              documents: state.documents.map((doc) =>
                doc.id === id
                  ? { ...doc, ...updates, updated_at: new Date().toISOString() }
                  : doc
              ),
            }
          }
        })
      },

      deleteDocument: (id) => {
        set((state) => {
          // Check which array the document belongs to
          const isInRealVault = state.realVaultDocuments.some(doc => doc.id === id)
          const isInDecoyVault = state.decoyVaultDocuments.some(doc => doc.id === id)

          if (isInRealVault) {
            return {
              realVaultDocuments: state.realVaultDocuments.filter((doc) => doc.id !== id),
              activeDocumentId: state.activeDocumentId === id ? null : state.activeDocumentId,
            }
          } else if (isInDecoyVault) {
            return {
              decoyVaultDocuments: state.decoyVaultDocuments.filter((doc) => doc.id !== id),
              activeDocumentId: state.activeDocumentId === id ? null : state.activeDocumentId,
            }
          } else {
            return {
              documents: state.documents.filter((doc) => doc.id !== id),
              activeDocumentId: state.activeDocumentId === id ? null : state.activeDocumentId,
            }
          }
        })
      },

      // Vault document getters
      getVaultDocuments: () => {
        const state = get()
        if (!state.vaultUnlocked || !state.currentVaultMode) {
          return []
        }
        return state.currentVaultMode === 'real'
          ? state.realVaultDocuments
          : state.decoyVaultDocuments
      },

      getRealVaultDocuments: () => {
        return get().realVaultDocuments
      },

      getDecoyVaultDocuments: () => {
        return get().decoyVaultDocuments
      },

      // Vault document management
      moveToVault: (docId, vaultMode) => {
        set((state) => {
          // Find the document in regular documents
          const doc = state.documents.find(d => d.id === docId)
          if (!doc) return state

          // Update document with vault mode
          const updatedDoc = { ...doc, vaultMode }

          // Remove from regular documents and add to appropriate vault
          const newDocuments = state.documents.filter(d => d.id !== docId)

          if (vaultMode === 'real') {
            return {
              documents: newDocuments,
              realVaultDocuments: [...state.realVaultDocuments, updatedDoc],
            }
          } else {
            return {
              documents: newDocuments,
              decoyVaultDocuments: [...state.decoyVaultDocuments, updatedDoc],
            }
          }
        })
      },

      removeFromVault: (docId) => {
        set((state) => {
          // Check which vault the document is in
          const realDoc = state.realVaultDocuments.find(d => d.id === docId)
          const decoyDoc = state.decoyVaultDocuments.find(d => d.id === docId)

          if (realDoc) {
            // Remove from real vault, add to regular documents
            const { vaultMode, ...docWithoutVaultMode } = realDoc
            return {
              realVaultDocuments: state.realVaultDocuments.filter(d => d.id !== docId),
              documents: [...state.documents, docWithoutVaultMode],
            }
          } else if (decoyDoc) {
            // Remove from decoy vault, add to regular documents
            const { vaultMode, ...docWithoutVaultMode } = decoyDoc
            return {
              decoyVaultDocuments: state.decoyVaultDocuments.filter(d => d.id !== docId),
              documents: [...state.documents, docWithoutVaultMode],
            }
          }

          return state
        })
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
      name: 'elohimos.docs',
      // Don't persist locked state, last activity, or vaultPassphrase (security)
      partialize: (state) => ({
        workspaceView: state.workspaceView,
        documents: state.documents,
        realVaultDocuments: state.realVaultDocuments,
        decoyVaultDocuments: state.decoyVaultDocuments,
        activeDocumentId: state.activeDocumentId,
        selectedInsightModel: state.selectedInsightModel,
        vaultSetupComplete: state.vaultSetupComplete,
        vaultPasswordHash: state.vaultPasswordHash,
        vaultPassword2Hash: state.vaultPassword2Hash,
        decoyPasswordHash: state.decoyPasswordHash,
        realVaultVerification: state.realVaultVerification,
        realVault2Verification: state.realVault2Verification,
        decoyVaultVerification: state.decoyVaultVerification,
        securitySettings: state.securitySettings,
        // vaultPassphrase is intentionally NOT persisted (memory only)
      }),
    }
  )
)
