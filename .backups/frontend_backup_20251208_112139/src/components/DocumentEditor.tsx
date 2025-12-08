/**
 * Document Editor
 *
 * Universal editor that handles:
 * - Doc: Rich text editing
 * - Sheet: Spreadsheet editing
 * - Insight: Voice transcription + AI analysis
 */

import { useState, useEffect, useRef } from 'react'
import { useDocsStore, type Document } from '@/stores/docsStore'
import { useUserStore } from '@/stores/userStore'
import { Save, Lock, Unlock, Shield, Upload, Sparkles, Loader2, Menu, Fingerprint, Trash2, Pencil, ShieldCheck } from 'lucide-react'
import toast from 'react-hot-toast'
import { SpreadsheetEditor } from './SpreadsheetEditor'
import { RichTextEditor } from './RichTextEditor'
import { ModelSelector } from './ModelSelector'
import {
  authenticateBiometric,
  registerBiometric,
  isBiometricAvailable,
  hasBiometricCredential,
} from '@/lib/biometricAuth'
import { encryptDocument, decryptDocument } from '@/lib/encryption'

interface DocumentEditorProps {
  document: Document
  onToggleSidebar?: () => void
  isSidebarCollapsed?: boolean
}

export function DocumentEditor({ document, onToggleSidebar, isSidebarCollapsed }: DocumentEditorProps) {
  const { updateDocument, lockDocument, unlockDocument, lockedDocuments, securitySettings, selectedInsightModel, setSelectedInsightModel } = useDocsStore()
  const { user } = useUserStore()
  const [content, setContent] = useState(document.content)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [biometricAvailable, setBiometricAvailable] = useState(false)
  const [hasBiometric, setHasBiometric] = useState(false)
  const [isDecrypting, setIsDecrypting] = useState(false)
  const [isEncrypted, setIsEncrypted] = useState(false)
  const [decryptionError, setDecryptionError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const isLocked = lockedDocuments.has(document.id)

  useEffect(() => {
    setContent(document.content)
    setHasUnsavedChanges(false)
    setDecryptionError(null)

    // Check if document is encrypted
    const isDocEncrypted = typeof document.content === 'object' && document.content?.encrypted === true
    setIsEncrypted(isDocEncrypted)
  }, [document.id])

  // Automatically decrypt encrypted documents on mount
  useEffect(() => {
    const handleDecryption = async () => {
      // Check if document is encrypted
      if (typeof document.content !== 'object' || document.content?.encrypted !== true) {
        return
      }

      // Get vault state
      const { vaultUnlocked, vaultPassphrase } = useDocsStore.getState()

      // If vault is locked, show error
      if (!vaultUnlocked || !vaultPassphrase) {
        setDecryptionError('Vault is locked. Please unlock vault to view this document.')
        return
      }

      // Decrypt the document
      setIsDecrypting(true)
      setDecryptionError(null)
      toast.loading('Decrypting document...', { id: 'decrypt' })

      try {
        // Prepare encrypted document structure
        const encryptedDoc = {
          id: document.id,
          title: document.title,
          encrypted_content: document.content.encrypted_content,
          salt: document.content.salt,
          iv: document.content.iv,
          created_at: document.created_at,
          modified_at: document.updated_at,
          metadata: document.content.metadata
        }

        // Decrypt the content
        const decryptedContent = await decryptDocument(encryptedDoc, vaultPassphrase)

        // Parse the decrypted content (it was stringified during encryption)
        let parsedContent
        try {
          parsedContent = JSON.parse(decryptedContent)
        } catch {
          // If it's not JSON, use as plain text
          parsedContent = decryptedContent
        }

        // Update the content state with decrypted content
        setContent(parsedContent)
        toast.success('Document decrypted successfully!', { id: 'decrypt' })
      } catch (error) {
        console.error('Decryption error:', error)
        setDecryptionError('Failed to decrypt document. The passphrase may be incorrect.')
        toast.error('Failed to decrypt document', { id: 'decrypt' })
      } finally {
        setIsDecrypting(false)
      }
    }

    handleDecryption()
  }, [document.id, document.content])

  // Check biometric availability on mount
  useEffect(() => {
    const checkBiometric = async () => {
      const available = await isBiometricAvailable()
      setBiometricAvailable(available)

      if (available) {
        const hasCredential = hasBiometricCredential(document.id)
        setHasBiometric(hasCredential)
      }
    }

    checkBiometric()
  }, [document.id])

  const handleContentChange = (newContent: any) => {
    setContent(newContent)
    setHasUnsavedChanges(true)
  }

  const handleSave = () => {
    updateDocument(document.id, { content })
    setHasUnsavedChanges(false)
  }

  const handleToggleLock = async () => {
    if (isLocked) {
      // Unlock - requires authentication if Touch ID is enabled
      if (securitySettings.require_touch_id && biometricAvailable) {
        const authenticated = await authenticateBiometric(document.id)

        if (!authenticated) {
          toast.error('Authentication failed. Document remains locked.')
          return
        }

        toast.success('Authenticated! Document unlocked.')
      }

      unlockDocument(document.id)
    } else {
      // Lock - optionally register biometric
      lockDocument(document.id)

      // If Touch ID is enabled and document doesn't have credential yet, register it
      if (securitySettings.require_touch_id && biometricAvailable && !hasBiometric && user) {
        const registered = await registerBiometric(document.id, user.user_id)

        if (registered) {
          setHasBiometric(true)
          toast.success('Touch ID registered for this document')
        }
      }
    }
  }

  const handleVoiceUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // Check file type
    const validTypes = ['audio/m4a', 'audio/mp4', 'audio/x-m4a', 'audio/mpeg', 'audio/wav', 'audio/webm']
    if (!validTypes.includes(file.type) && !file.name.endsWith('.m4a')) {
      toast.error('Please upload an audio file (.m4a, .mp3, .wav, .webm)')
      return
    }

    setIsTranscribing(true)
    toast.loading('Transcribing audio...', { id: 'transcribe' })

    try {
      const formData = new FormData()
      formData.append('audio_file', file)

      const response = await fetch('/api/v1/insights/transcribe', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Transcription failed')
      }

      const data = await response.json()

      // Update content with transcribed text
      const newContent = {
        ...content,
        raw: (content?.raw || '') + (content?.raw ? '\n\n' : '') + data.transcript,
        audio_file: file.name,
      }

      handleContentChange(newContent)
      handleSave()

      toast.success('Audio transcribed successfully!', { id: 'transcribe' })
    } catch (error) {
      console.error('Transcription error:', error)
      toast.error('Failed to transcribe audio', { id: 'transcribe' })
    } finally {
      setIsTranscribing(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleAnalyzeWithAI = async () => {
    if (!content?.raw || content.raw.trim().length === 0) {
      toast.error('Please add a transcript first')
      return
    }

    if (!selectedInsightModel) {
      toast.error('Please select a model first')
      return
    }

    setIsAnalyzing(true)
    toast.loading('Analyzing with AI...', { id: 'analyze' })

    try {
      const response = await fetch('/api/v1/insights/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transcript: content.raw,
          document_title: document.title,
          model: selectedInsightModel,
        }),
      })

      if (!response.ok) {
        throw new Error('Analysis failed')
      }

      const data = await response.json()

      // Update content with AI analysis
      const newContent = {
        ...content,
        analysis: data.analysis,
      }

      handleContentChange(newContent)
      handleSave()

      toast.success('Analysis complete!', { id: 'analyze' })
    } catch (error) {
      console.error('Analysis error:', error)
      toast.error('Failed to analyze transcript', { id: 'analyze' })
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleSaveToVault = async () => {
    // First save the document
    handleSave()

    // Check if vault is setup
    const { vaultSetupComplete, vaultUnlocked, vaultPassphrase, updateDocument } = useDocsStore.getState()

    if (!vaultSetupComplete) {
      toast.error('Vault not setup. Please setup your vault first.')
      return
    }

    // If vault is locked, trigger authentication
    if (!vaultUnlocked || !vaultPassphrase) {
      toast.error('Please unlock vault first from the Vault tab')
      return
    }

    toast.loading('Encrypting and saving to vault...', { id: 'save-vault' })

    try {
      // Serialize document content to string
      const contentString = typeof document.content === 'string'
        ? document.content
        : JSON.stringify(document.content)

      // Encrypt the document
      const encryptedDoc = await encryptDocument(
        document.id,
        document.title,
        contentString,
        vaultPassphrase
      )

      // Update the document with encryption metadata
      updateDocument(document.id, {
        security_level: 'encrypted',
        is_private: true,
        // Store encryption metadata in content
        content: {
          encrypted: true,
          encrypted_content: encryptedDoc.encrypted_content,
          salt: encryptedDoc.salt,
          iv: encryptedDoc.iv,
          metadata: encryptedDoc.metadata
        }
      })

      toast.success('Document encrypted and saved to vault!', { id: 'save-vault' })
    } catch (error) {
      console.error('Save to vault error:', error)
      toast.error('Failed to encrypt document', { id: 'save-vault' })
    }
  }

  // Render different editors based on document type
  const renderEditor = () => {
    // Show decryption loading state
    if (isDecrypting) {
      return (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Loader2 className="w-16 h-16 mx-auto mb-4 text-primary-600 animate-spin" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Decrypting Document
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Please wait while we decrypt your document...
            </p>
          </div>
        </div>
      )
    }

    // Show decryption error state
    if (decryptionError) {
      return (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center max-w-md">
            <Lock className="w-16 h-16 mx-auto mb-4 text-red-500" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Cannot Decrypt Document
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              {decryptionError}
            </p>
            <button
              onClick={() => {
                const { workspaceView, setWorkspaceView } = useDocsStore.getState()
                if (workspaceView !== 'vault') {
                  setWorkspaceView('vault')
                  toast.success('Switched to Vault tab. Please unlock the vault.')
                }
              }}
              className="inline-flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm font-medium transition-colors"
            >
              <Shield size={18} />
              Go to Vault
            </button>
          </div>
        </div>
      )
    }

    if (isLocked) {
      return (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Lock className="w-16 h-16 mx-auto mb-4 text-gray-400" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Document Locked
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              {document.type === 'insight'
                ? 'This insight is locked for your privacy'
                : 'This document is locked'}
            </p>
            <button
              onClick={handleToggleLock}
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium transition-colors"
            >
              {biometricAvailable && hasBiometric ? (
                <>
                  <Fingerprint size={18} />
                  Unlock with Touch ID
                </>
              ) : (
                <>
                  <Unlock size={18} />
                  Unlock
                </>
              )}
            </button>
            {biometricAvailable && !hasBiometric && (
              <p className="mt-3 text-xs text-gray-400">
                Touch ID will be registered when you lock this document
              </p>
            )}
          </div>
        </div>
      )
    }

    switch (document.type) {
      case 'doc':
        return (
          <div className="flex-1 flex flex-col">
            <RichTextEditor
              value={typeof content === 'string' ? content : ''}
              onChange={handleContentChange}
              placeholder="Start writing..."
              disabled={false}
            />
          </div>
        )

      case 'sheet':
        return (
          <SpreadsheetEditor
            data={content || { rows: [], columns: [] }}
            onChange={handleContentChange}
            onSave={handleSave}
          />
        )

      case 'insight':
        return (
          <div className="flex-1 flex flex-col">
            {/* Toolbar */}
            <div className="flex items-center gap-1 p-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
              {/* Upload Audio */}
              <input
                ref={fileInputRef}
                type="file"
                accept="audio/*,.m4a"
                onChange={handleVoiceUpload}
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isTranscribing}
                className="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title="Upload voice memo (.m4a, .mp3, .wav)"
              >
                {isTranscribing ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Upload className="w-4 h-4" />
                )}
              </button>

              {/* Analyze with AI */}
              <button
                onClick={handleAnalyzeWithAI}
                disabled={isAnalyzing || !content?.raw || content.raw.trim().length === 0}
                className="p-2 rounded hover:bg-primary-100 dark:hover:bg-primary-900/30 text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title="Analyze transcript with AI"
              >
                {isAnalyzing ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4" />
                )}
              </button>

              {/* Clear Transcript */}
              <button
                onClick={() => handleContentChange({ ...content, raw: '' })}
                disabled={!content?.raw || content.raw.trim().length === 0}
                className="p-2 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600 dark:text-red-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title="Clear transcript"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>

            {/* Content Area - Top/Bottom Split */}
            <div className="flex-1 flex flex-col min-h-0">
              {/* Raw Transcript - 60% */}
              <div className="flex-[3] flex flex-col border-b border-gray-200 dark:border-gray-700 min-h-0">
                <div className="px-4 py-2 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700">
                  <h3 className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide">
                    Raw Transcript
                  </h3>
                </div>
                <textarea
                  value={typeof content?.raw === 'string' ? content.raw : ''}
                  onChange={(e) =>
                    handleContentChange({ ...content, raw: e.target.value })
                  }
                  placeholder="Paste your transcript or upload an audio file..."
                  className="flex-1 p-4 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary-500 resize-none text-sm"
                  disabled={isTranscribing}
                />
              </div>

              {/* AI Analysis - 40% */}
              <div className="flex-[2] flex flex-col min-h-0">
                <div className="px-4 py-2 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700">
                  <h3 className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide">
                    AI Analysis
                  </h3>
                </div>
                {content?.analysis ? (
                  <textarea
                    value={content.analysis}
                    readOnly
                    className="flex-1 p-4 bg-gray-50 dark:bg-gray-800/50 text-gray-900 dark:text-gray-100 focus:outline-none resize-none text-sm select-text cursor-text"
                    placeholder="Analysis will appear here..."
                  />
                ) : (
                  <div className="flex-1 flex items-center justify-center bg-gray-50 dark:bg-gray-800/50">
                    <div className="text-center text-gray-400">
                      <Sparkles className="w-12 h-12 mx-auto mb-3 opacity-30" />
                      <p className="text-sm">No analysis yet</p>
                      <p className="text-xs mt-2">
                        Add transcript and click "Analyze"
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-gray-200 dark:border-gray-700">
        {/* Left side - Hamburger + Model Selector (for Insights) */}
        <div className="flex items-center gap-3 flex-1">
          {onToggleSidebar && (
            <button
              onClick={onToggleSidebar}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors text-gray-600 dark:text-gray-400"
              title={isSidebarCollapsed ? "Show sidebar" : "Hide sidebar"}
            >
              <Menu className="w-5 h-5" />
            </button>
          )}
          {document.type === 'insight' && (
            <ModelSelector
              value={selectedInsightModel}
              onChange={setSelectedInsightModel}
            />
          )}
        </div>

        {/* Center - Document Title with Pencil Hover and Encryption Badge */}
        <div className="flex items-center gap-2 group">
          <input
            type="text"
            value={document.title}
            onChange={(e) => updateDocument(document.id, { title: e.target.value })}
            className="text-lg font-semibold bg-transparent border-none focus:outline-none text-gray-900 dark:text-gray-100 text-center min-w-[200px]"
            disabled={isLocked}
          />
          <Pencil className="w-4 h-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
          {isEncrypted && (
            <button
              onClick={() => {
                const metadata = document.content?.metadata
                const info = metadata
                  ? `Encrypted Document\n\nOriginal size: ${metadata.original_size} bytes\nEncrypted size: ${metadata.encrypted_size} bytes\nCompression: ${((1 - metadata.encrypted_size / metadata.original_size) * 100).toFixed(1)}%`
                  : 'This document is encrypted and stored securely in the vault.'
                toast.success(info, { duration: 5000 })
              }}
              className="flex items-center gap-1 px-2 py-1 bg-amber-100 dark:bg-amber-900/30 rounded text-xs text-amber-700 dark:text-amber-400 hover:bg-amber-200 dark:hover:bg-amber-900/50 transition-colors"
              title="Click to view encryption details"
            >
              <Lock className="w-3 h-3" />
              <span>Encrypted</span>
            </button>
          )}
        </div>

        {/* Right side - Actions */}
        <div className="flex items-center gap-2 flex-1 justify-end">
          {hasUnsavedChanges && (
            <>
              <button
                onClick={handleSave}
                className="flex items-center gap-2 px-3 py-1.5 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium transition-all"
              >
                <Save className="w-4 h-4" />
                <span>Save</span>
              </button>
              <button
                onClick={handleSaveToVault}
                className="flex items-center gap-2 px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm font-medium transition-all"
                title="Save to Secure Vault"
              >
                <ShieldCheck className="w-4 h-4" />
                <span>Save to Vault</span>
              </button>
            </>
          )}

          {document.type === 'insight' && (
            <>
              {/* Lock button */}
              <button
                onClick={handleToggleLock}
                className={`relative p-2 rounded transition-colors ${
                  isLocked
                    ? 'text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-gray-100'
                }`}
                title={
                  isLocked
                    ? biometricAvailable && hasBiometric
                      ? 'Unlock with Touch ID'
                      : 'Unlock'
                    : 'Lock'
                }
              >
                {isLocked ? <Lock className="w-4 h-4" /> : <Unlock className="w-4 h-4" />}
                {biometricAvailable && hasBiometric && isLocked && (
                  <Fingerprint className="absolute -top-1 -right-1 w-3 h-3 text-primary-600 dark:text-primary-400" />
                )}
              </button>

              {/* Private badge - always shown for insights */}
              {document.is_private && (
                <div className="flex items-center gap-1 px-2 py-1 bg-amber-100 dark:bg-amber-900/30 rounded text-xs text-amber-700 dark:text-amber-400">
                  <Shield className="w-3 h-3" />
                  <span>Private</span>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Editor */}
      {renderEditor()}
    </div>
  )
}
