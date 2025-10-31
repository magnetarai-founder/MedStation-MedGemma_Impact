/**
 * Vault Workspace
 *
 * Secure file browser (Proton Drive style) with Touch ID + Password authentication
 */

import { useState, useEffect } from 'react'
import { useDocsStore } from '@/stores/docsStore'
import { Lock, Fingerprint, AlertTriangle, FileText, Table2, Lightbulb, Eye, EyeOff, Grid3x3, List, Search, Plus, MoreVertical, Shield, Clock, HardDrive, FolderOpen, Filter, SlidersHorizontal, ArrowUpDown } from 'lucide-react'
import { authenticateBiometric, isBiometricAvailable } from '@/lib/biometricAuth'
import toast from 'react-hot-toast'
import type { Document, DocumentType } from '@/stores/docsStore'
import { decryptDocument } from '@/lib/encryption'

export function VaultWorkspace() {
  const {
    vaultUnlocked,
    unlockVault,
    lockVault,
    currentVaultMode,
    securitySettings,
    getVaultDocuments,
    setActiveDocument,
    setWorkspaceView,
    createDocument,
    deleteDocument,
    removeFromVault,
    vaultPassphrase,
    updateDocument
  } = useDocsStore()
  const requireTouchID = securitySettings.require_touch_id
  const [isAuthenticating, setIsAuthenticating] = useState(false)
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [biometricAvailable, setBiometricAvailable] = useState(false)
  const [authError, setAuthError] = useState('')

  // Vault content state
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [searchQuery, setSearchQuery] = useState('')
  const [showCreateMenu, setShowCreateMenu] = useState(false)
  const [contextMenu, setContextMenu] = useState<{ docId: string; x: number; y: number } | null>(null)
  const [filterType, setFilterType] = useState<'all' | DocumentType>('all')
  const [sortBy, setSortBy] = useState<'name' | 'created' | 'modified'>('modified')
  const [showFilters, setShowFilters] = useState(false)
  const [stealthLabelModal, setStealthLabelModal] = useState<{ docId: string; currentLabel: string } | null>(null)
  const [stealthLabelInput, setStealthLabelInput] = useState('')

  useEffect(() => {
    checkBiometric()
  }, [])

  const checkBiometric = async () => {
    const available = await isBiometricAvailable()
    setBiometricAvailable(available)
  }

  const handleUnlock = async () => {
    setAuthError('')
    setIsAuthenticating(true)

    try {
      // Step 1: Touch ID authentication (only if required)
      if (requireTouchID) {
        if (biometricAvailable) {
          const biometricSuccess = await authenticateBiometric()
          if (!biometricSuccess) {
            setAuthError('Touch ID authentication failed')
            setIsAuthenticating(false)
            return
          }
        } else {
          setAuthError('Touch ID is required but not available on this device')
          setIsAuthenticating(false)
          return
        }
      }

      // Step 2: Password authentication
      if (!password) {
        setAuthError('Please enter your vault password')
        setIsAuthenticating(false)
        return
      }

      const success = await unlockVault(password)
      if (!success) {
        setAuthError('Incorrect password')
        setPassword('')
        setIsAuthenticating(false)
        return
      }

      // Success!
      setPassword('')
      toast.success(currentVaultMode === 'decoy' ? 'Vault unlocked' : 'Vault unlocked')
      setIsAuthenticating(false)
    } catch (error) {
      console.error('Vault unlock error:', error)
      setAuthError('Authentication failed')
      setIsAuthenticating(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleUnlock()
    }
  }

  // Get vault documents and apply filters
  const vaultDocs = getVaultDocuments()

  const filteredDocs = vaultDocs
    .filter(doc => {
      // Search filter (title and content)
      const matchesSearch = searchQuery === '' ||
        doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (typeof doc.content === 'string' && doc.content.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (typeof doc.content === 'object' && JSON.stringify(doc.content).toLowerCase().includes(searchQuery.toLowerCase()))

      // Type filter
      const matchesType = filterType === 'all' || doc.type === filterType

      return matchesSearch && matchesType
    })
    .sort((a, b) => {
      // Sort logic
      switch (sortBy) {
        case 'name':
          return a.title.localeCompare(b.title)
        case 'created':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        case 'modified':
          return new Date(b.updated_at || b.created_at).getTime() - new Date(a.updated_at || a.created_at).getTime()
        default:
          return 0
      }
    })

  // Helper functions
  const getDocumentIcon = (type: DocumentType) => {
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

  const getDisplayTitle = (doc: Document) => {
    // If stealth labels are enabled and document has a stealth label, use it
    if (securitySettings.stealth_labels && doc.stealth_label) {
      return doc.stealth_label
    }
    // Otherwise use real title
    return doc.title
  }

  const formatFileSize = (doc: Document) => {
    // Estimate size based on content
    const contentSize = JSON.stringify(doc.content).length
    if (contentSize < 1024) return `${contentSize}B`
    if (contentSize < 1024 * 1024) return `${(contentSize / 1024).toFixed(1)}KB`
    return `${(contentSize / (1024 * 1024)).toFixed(1)}MB`
  }

  const formatDate = (dateString: string) => {
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

  // Document actions
  const handleOpenDocument = async (doc: Document) => {
    // Check if document is encrypted
    if (doc.security_level === 'encrypted') {
      if (!vaultPassphrase) {
        toast.error('Vault passphrase not available. Please unlock vault again.')
        return
      }

      try {
        toast.loading('Decrypting document...', { id: 'decrypt' })

        // Prepare encrypted document structure
        const encryptedDoc = {
          id: doc.id,
          title: doc.title,
          encrypted_content: doc.content.encrypted_content,
          salt: doc.content.salt,
          iv: doc.content.iv,
          created_at: doc.created_at,
          modified_at: doc.updated_at,
          metadata: doc.content.metadata
        }

        // Decrypt the document
        const decryptedString = await decryptDocument(encryptedDoc, vaultPassphrase)

        // Parse decrypted content
        let decryptedContent
        try {
          decryptedContent = JSON.parse(decryptedString)
        } catch {
          decryptedContent = decryptedString
        }

        // Update document with decrypted content
        updateDocument(doc.id, {
          content: decryptedContent,
          security_level: 'standard', // Temporarily mark as standard while editing
        })

        toast.success('Document decrypted and opened', { id: 'decrypt' })
        setActiveDocument(doc.id)
        setWorkspaceView('docs')
      } catch (error) {
        console.error('Decryption error:', error)
        toast.error('Failed to decrypt document. Incorrect passphrase?', { id: 'decrypt' })
      }
    } else {
      // Document not encrypted, open directly
      setActiveDocument(doc.id)
      setWorkspaceView('docs')
      toast.success('Document opened')
    }
  }

  const handleCreateDocument = (type: DocumentType) => {
    const doc = createDocument(type)
    setShowCreateMenu(false)
    toast.success(`Secure ${type} created and encrypted`)
    // Auto-open the new document
    setActiveDocument(doc.id)
    setWorkspaceView('docs')
  }

  const handleDeleteDocument = (docId: string) => {
    if (confirm('Delete this document? This action cannot be undone.')) {
      deleteDocument(docId)
      toast.success('Document deleted')
      setContextMenu(null)
    }
  }

  const handleMoveToRegular = (docId: string) => {
    if (confirm('Move this document to regular workspace? It will be decrypted.')) {
      removeFromVault(docId)
      toast.success('Document moved to regular workspace')
      setContextMenu(null)
    }
  }

  const handleSetStealthLabel = (docId: string) => {
    const doc = vaultDocs.find(d => d.id === docId)
    if (doc) {
      setStealthLabelModal({ docId, currentLabel: doc.stealth_label || '' })
      setStealthLabelInput(doc.stealth_label || '')
    }
    setContextMenu(null)
  }

  const handleSaveStealthLabel = () => {
    if (stealthLabelModal) {
      updateDocument(stealthLabelModal.docId, {
        stealth_label: stealthLabelInput.trim() || undefined
      })
      toast.success(stealthLabelInput.trim() ? 'Stealth label set' : 'Stealth label removed')
      setStealthLabelModal(null)
      setStealthLabelInput('')
    }
  }

  const handleContextMenu = (e: React.MouseEvent, docId: string) => {
    e.preventDefault()
    setContextMenu({ docId, x: e.clientX, y: e.clientY })
  }

  // Close context menu on click
  useEffect(() => {
    const handleClick = () => setContextMenu(null)
    if (contextMenu) {
      document.addEventListener('click', handleClick)
      return () => document.removeEventListener('click', handleClick)
    }
  }, [contextMenu])

  // Locked State - Show Authentication
  if (!vaultUnlocked) {
    return (
      <div className="h-full flex items-center justify-center bg-gradient-to-br from-amber-50 to-orange-50 dark:from-gray-900 dark:to-gray-800">
        <div className="max-w-md w-full mx-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl p-8">
            {/* Header */}
            <div className="text-center mb-6">
              <div className="w-20 h-20 bg-amber-100 dark:bg-amber-900/30 rounded-full flex items-center justify-center mx-auto mb-4 relative">
                <Lock className="w-10 h-10 text-amber-600 dark:text-amber-400" />
                {biometricAvailable && requireTouchID && (
                  <Fingerprint className="absolute -top-2 -right-2 w-8 h-8 text-blue-600 dark:text-blue-400" />
                )}
              </div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                Secure Vault
              </h2>
              <p className="text-gray-600 dark:text-gray-400 text-sm">
                {requireTouchID
                  ? 'Touch ID and password required'
                  : 'Password required'
                }
              </p>
            </div>

            {/* Error Message */}
            {authError && (
              <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-2">
                <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0" />
                <p className="text-sm text-red-700 dark:text-red-300">{authError}</p>
              </div>
            )}

            {/* Password Input */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Vault Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Enter your password"
                  disabled={isAuthenticating}
                  className="w-full px-4 py-3 pr-12 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-amber-500 focus:border-transparent disabled:opacity-50"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            {/* Unlock Button */}
            <button
              onClick={handleUnlock}
              disabled={isAuthenticating || !password}
              className="w-full py-3 bg-amber-600 hover:bg-amber-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {biometricAvailable && <Fingerprint className="w-5 h-5" />}
              {isAuthenticating ? 'Authenticating...' : 'Unlock Vault'}
            </button>

            {/* Info */}
            <p className="mt-4 text-xs text-center text-gray-500 dark:text-gray-400">
              Both Touch ID and password verification required
            </p>
          </div>
        </div>
      </div>
    )
  }

  // Unlocked State - Show Vault Contents
  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-900">
      {/* Vault Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-900/10 dark:to-orange-900/10">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            <Lock className="w-5 h-5 text-amber-600 dark:text-amber-400" />
            <div>
              <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">
                Secure Vault
              </h2>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                {currentVaultMode === 'decoy' ? 'Standard Mode' : 'Protected Mode'}
              </p>
            </div>
          </div>
          {/* Document count badge */}
          <div className="flex items-center gap-2 px-3 py-1.5 bg-white/50 dark:bg-gray-800/50 rounded-full">
            <HardDrive className="w-4 h-4 text-amber-600 dark:text-amber-400" />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {vaultDocs.length} {vaultDocs.length === 1 ? 'document' : 'documents'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Create New Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowCreateMenu(!showCreateMenu)}
              className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Create New
            </button>
            {showCreateMenu && (
              <div className="absolute top-full right-0 mt-2 w-56 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 py-1 z-10">
                <button
                  onClick={() => handleCreateDocument('doc')}
                  className="w-full px-4 py-2.5 text-left hover:bg-blue-50 dark:hover:bg-blue-900/20 flex items-center gap-3 transition-colors"
                >
                  <FileText className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Secure Document
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      Auto-encrypted text document
                    </div>
                  </div>
                </button>
                <button
                  onClick={() => handleCreateDocument('sheet')}
                  className="w-full px-4 py-2.5 text-left hover:bg-green-50 dark:hover:bg-green-900/20 flex items-center gap-3 transition-colors"
                >
                  <Table2 className="w-5 h-5 text-green-600 dark:text-green-400" />
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Secure Spreadsheet
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      Auto-encrypted data table
                    </div>
                  </div>
                </button>
                <button
                  onClick={() => handleCreateDocument('insight')}
                  className="w-full px-4 py-2.5 text-left hover:bg-amber-50 dark:hover:bg-amber-900/20 flex items-center gap-3 transition-colors"
                >
                  <Lightbulb className="w-5 h-5 text-amber-600 dark:text-amber-400" />
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Secure Insight
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      Auto-encrypted AI analysis
                    </div>
                  </div>
                </button>
              </div>
            )}
          </div>

          {/* Lock Vault Button */}
          <button
            onClick={lockVault}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
          >
            <Lock className="w-4 h-4" />
            Lock Vault
          </button>
        </div>
      </div>

      {/* Vault Content - Proton Drive Style */}
      <div className="flex-1 p-6 overflow-auto">
        <div className="max-w-6xl mx-auto">
          {/* Results Counter */}
          {vaultDocs.length > 0 && (
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {filteredDocs.length === vaultDocs.length ? (
                  <span>{vaultDocs.length} document{vaultDocs.length !== 1 ? 's' : ''}</span>
                ) : (
                  <span>{filteredDocs.length} of {vaultDocs.length} documents</span>
                )}
              </p>
              {(searchQuery || filterType !== 'all') && (
                <button
                  onClick={() => {
                    setSearchQuery('')
                    setFilterType('all')
                  }}
                  className="text-sm text-amber-600 dark:text-amber-400 hover:underline"
                >
                  Clear filters
                </button>
              )}
            </div>
          )}

          {/* Toolbar */}
          <div className="flex items-center gap-3 mb-6">
            {/* Search Bar */}
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search vault documents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-amber-500 focus:border-transparent text-sm"
              />
            </div>

            {/* Filter by Type */}
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value as any)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-amber-500 focus:border-transparent"
            >
              <option value="all">All Types</option>
              <option value="doc">Documents</option>
              <option value="sheet">Spreadsheets</option>
              <option value="insight">Insights</option>
            </select>

            {/* Sort By */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-amber-500 focus:border-transparent"
            >
              <option value="modified">Recently Modified</option>
              <option value="created">Recently Created</option>
              <option value="name">Name (A-Z)</option>
            </select>

            {/* View Toggle */}
            <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-2 rounded ${
                  viewMode === 'grid'
                    ? 'bg-white dark:bg-gray-700 text-amber-600 dark:text-amber-400 shadow-sm'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
              >
                <Grid3x3 className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-2 rounded ${
                  viewMode === 'list'
                    ? 'bg-white dark:bg-gray-700 text-amber-600 dark:text-amber-400 shadow-sm'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
              >
                <List className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Empty State */}
          {filteredDocs.length === 0 && vaultDocs.length === 0 && (
            <div className="text-center py-12">
              <div className="w-24 h-24 bg-amber-100 dark:bg-amber-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                <FolderOpen className="w-12 h-12 text-amber-600 dark:text-amber-400" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                Your Vault is Empty
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                Create encrypted documents using the "Create New" button above
              </p>

              {/* Quick Actions */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-2xl mx-auto mt-8">
                <button
                  onClick={() => handleCreateDocument('doc')}
                  className="p-6 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg hover:border-blue-500 dark:hover:border-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-all group"
                >
                  <FileText className="w-8 h-8 text-gray-400 group-hover:text-blue-600 dark:group-hover:text-blue-400 mx-auto mb-2" />
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300 group-hover:text-blue-600 dark:group-hover:text-blue-400">
                    Secure Document
                  </p>
                </button>
                <button
                  onClick={() => handleCreateDocument('sheet')}
                  className="p-6 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg hover:border-green-500 dark:hover:border-green-400 hover:bg-green-50 dark:hover:bg-green-900/10 transition-all group"
                >
                  <Table2 className="w-8 h-8 text-gray-400 group-hover:text-green-600 dark:group-hover:text-green-400 mx-auto mb-2" />
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300 group-hover:text-green-600 dark:group-hover:text-green-400">
                    Secure Spreadsheet
                  </p>
                </button>
                <button
                  onClick={() => handleCreateDocument('insight')}
                  className="p-6 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg hover:border-amber-500 dark:hover:border-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/10 transition-all group"
                >
                  <Lightbulb className="w-8 h-8 text-gray-400 group-hover:text-amber-600 dark:group-hover:text-amber-400 mx-auto mb-2" />
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300 group-hover:text-amber-600 dark:group-hover:text-amber-400">
                    Secure Insight
                  </p>
                </button>
              </div>
            </div>
          )}

          {/* No Search Results */}
          {filteredDocs.length === 0 && vaultDocs.length > 0 && (
            <div className="text-center py-12">
              <div className="w-20 h-20 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
                <Search className="w-10 h-10 text-gray-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                No documents found
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Try adjusting your search query
              </p>
            </div>
          )}

          {/* Document Grid */}
          {filteredDocs.length > 0 && viewMode === 'grid' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredDocs.map((doc) => {
                const Icon = getDocumentIcon(doc.type)
                return (
                  <div
                    key={doc.id}
                    onClick={() => handleOpenDocument(doc)}
                    onContextMenu={(e) => handleContextMenu(e, doc.id)}
                    className="group relative p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-amber-500 dark:hover:border-amber-400 hover:shadow-lg transition-all cursor-pointer"
                  >
                    {/* Document Icon & Type */}
                    <div className="flex items-start justify-between mb-3">
                      <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                        doc.type === 'doc' ? 'bg-blue-100 dark:bg-blue-900/30' :
                        doc.type === 'sheet' ? 'bg-green-100 dark:bg-green-900/30' :
                        'bg-amber-100 dark:bg-amber-900/30'
                      }`}>
                        <Icon className={`w-6 h-6 ${
                          doc.type === 'doc' ? 'text-blue-600 dark:text-blue-400' :
                          doc.type === 'sheet' ? 'text-green-600 dark:text-green-400' :
                          'text-amber-600 dark:text-amber-400'
                        }`} />
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleContextMenu(e, doc.id)
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-opacity"
                      >
                        <MoreVertical className="w-4 h-4 text-gray-500" />
                      </button>
                    </div>

                    {/* Document Title */}
                    <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-1 truncate">
                      {getDisplayTitle(doc)}
                    </h3>

                    {/* Metadata */}
                    <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                      <div className="flex items-center gap-1">
                        <Shield className="w-3 h-3 text-amber-600 dark:text-amber-400" />
                        <span>Encrypted</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        <span>{formatDate(doc.updated_at)}</span>
                      </div>
                    </div>

                    {/* File Size */}
                    <div className="mt-2 text-xs text-gray-400 dark:text-gray-500">
                      {formatFileSize(doc)}
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* Document List */}
          {filteredDocs.length > 0 && viewMode === 'list' && (
            <div className="space-y-2">
              {filteredDocs.map((doc) => {
                const Icon = getDocumentIcon(doc.type)
                return (
                  <div
                    key={doc.id}
                    onClick={() => handleOpenDocument(doc)}
                    onContextMenu={(e) => handleContextMenu(e, doc.id)}
                    className="group flex items-center gap-4 p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-amber-500 dark:hover:border-amber-400 hover:shadow-md transition-all cursor-pointer"
                  >
                    {/* Icon */}
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      doc.type === 'doc' ? 'bg-blue-100 dark:bg-blue-900/30' :
                      doc.type === 'sheet' ? 'bg-green-100 dark:bg-green-900/30' :
                      'bg-amber-100 dark:bg-amber-900/30'
                    }`}>
                      <Icon className={`w-5 h-5 ${
                        doc.type === 'doc' ? 'text-blue-600 dark:text-blue-400' :
                        doc.type === 'sheet' ? 'text-green-600 dark:text-green-400' :
                        'text-amber-600 dark:text-amber-400'
                      }`} />
                    </div>

                    {/* Title & Metadata */}
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-gray-900 dark:text-gray-100 truncate">
                        {getDisplayTitle(doc)}
                      </h3>
                      <div className="flex items-center gap-3 mt-1">
                        <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                          <Shield className="w-3 h-3 text-amber-600 dark:text-amber-400" />
                          <span>Encrypted</span>
                        </div>
                        <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                          <Clock className="w-3 h-3" />
                          <span>{formatDate(doc.updated_at)}</span>
                        </div>
                        <span className="text-xs text-gray-400 dark:text-gray-500">
                          {formatFileSize(doc)}
                        </span>
                      </div>
                    </div>

                    {/* Actions */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleContextMenu(e, doc.id)
                      }}
                      className="opacity-0 group-hover:opacity-100 p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-opacity"
                    >
                      <MoreVertical className="w-4 h-4 text-gray-500" />
                    </button>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* Context Menu */}
      {contextMenu && (
        <div
          className="fixed bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 py-1 z-50"
          style={{ top: contextMenu.y, left: contextMenu.x }}
        >
          <button
            onClick={() => {
              const doc = vaultDocs.find(d => d.id === contextMenu.docId)
              if (doc) handleOpenDocument(doc)
            }}
            className="w-full px-4 py-2 text-left hover:bg-blue-50 dark:hover:bg-blue-900/20 flex items-center gap-3 text-sm"
          >
            <FolderOpen className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            <span className="text-gray-700 dark:text-gray-300">Open</span>
          </button>
          <button
            onClick={() => handleSetStealthLabel(contextMenu.docId)}
            className="w-full px-4 py-2 text-left hover:bg-purple-50 dark:hover:bg-purple-900/20 flex items-center gap-3 text-sm"
          >
            <EyeOff className="w-4 h-4 text-purple-600 dark:text-purple-400" />
            <span className="text-gray-700 dark:text-gray-300">Set Stealth Label</span>
          </button>
          <button
            onClick={() => handleMoveToRegular(contextMenu.docId)}
            className="w-full px-4 py-2 text-left hover:bg-amber-50 dark:hover:bg-amber-900/20 flex items-center gap-3 text-sm"
          >
            <Lock className="w-4 h-4 text-amber-600 dark:text-amber-400" />
            <span className="text-gray-700 dark:text-gray-300">Move to Regular Docs</span>
          </button>
          <div className="border-t border-gray-200 dark:border-gray-700 my-1" />
          <button
            onClick={() => handleDeleteDocument(contextMenu.docId)}
            className="w-full px-4 py-2 text-left hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-3 text-sm"
          >
            <AlertTriangle className="w-4 h-4 text-red-600 dark:text-red-400" />
            <span className="text-red-700 dark:text-red-300">Delete</span>
          </button>
        </div>
      )}

      {/* Stealth Label Modal */}
      {stealthLabelModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-md p-6 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-3 mb-4">
              <EyeOff className="w-6 h-6 text-purple-600 dark:text-purple-400" />
              <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                Set Stealth Label
              </h3>
            </div>

            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Create an innocuous cover name for this document. When "Stealth Labels" is enabled in Security settings, this name will be shown instead of the real title.
            </p>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                Real Title
              </label>
              <div className="px-3 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-gray-900 dark:text-gray-100 text-sm">
                {vaultDocs.find(d => d.id === stealthLabelModal.docId)?.title}
              </div>
            </div>

            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                Stealth Label (Cover Name)
              </label>
              <input
                type="text"
                value={stealthLabelInput}
                onChange={(e) => setStealthLabelInput(e.target.value)}
                placeholder="e.g., Grocery List.txt"
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                autoFocus
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Leave blank to remove stealth label
              </p>
            </div>

            <div className="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3 mb-6 border border-amber-200 dark:border-amber-800">
              <p className="text-xs text-amber-800 dark:text-amber-200">
                <strong>Example:</strong> "Financial Report 2024.xlsx" could be labeled as "Recipe Book.txt"
              </p>
              <p className="text-xs text-amber-700 dark:text-amber-300 mt-1">
                Provides plausible deniability during device searches. Real title visible when you open the document.
              </p>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setStealthLabelModal(null)
                  setStealthLabelInput('')
                }}
                className="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveStealthLabel}
                className="flex-1 px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-700 text-white transition-colors"
              >
                Save Label
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
