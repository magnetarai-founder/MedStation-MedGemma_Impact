/**
 * VaultWorkspace - Main Component
 * Modular refactored version of VaultWorkspace
 */

import { useState, useEffect, useRef } from 'react'
import { Lock, Fingerprint, AlertTriangle, Eye, EyeOff, Upload, File, X, Search } from 'lucide-react'
import { useDocsStore } from '@/stores/docsStore'
import toast from 'react-hot-toast'
import axios from 'axios'
import { decryptDocument } from '@/lib/encryption'
import { ContextBadge } from '../ContextBadge'

// Hooks
import {
  useVaultAuth,
  useVaultWorkspace,
  useFileOperations,
  useSelection,
  useDragDrop,
  useWebSocket,
  useAutoLock
} from './hooks'

// UI Components
import { Toolbar } from './Toolbar'
import { Breadcrumbs } from './Breadcrumbs'
import { FolderGrid } from './FolderGrid'
import { FileGrid } from './FileGrid'
import { EmptyState } from './EmptyState'

// Modals
import { DeleteConfirmModal } from './modals/DeleteConfirmModal'
import { RenameModal } from './modals/RenameModal'
import { NewFolderModal } from './modals/NewFolderModal'
import { MoveFileModal } from './modals/MoveFileModal'
import { TagManagementModal } from './modals/TagManagementModal'
import { StealthLabelModal } from './modals/StealthLabelModal'
import { StorageDashboardModal } from './modals/StorageDashboardModal'
import { TrashBinModal } from './modals/TrashBinModal'
import { ShareDialogModal } from './modals/ShareDialogModal'
import { VersionHistoryModal } from './modals/VersionHistoryModal'
import { CommentsModal } from './modals/CommentsModal'
import { PinnedFilesModal } from './modals/PinnedFilesModal'
import { AuditLogsModal } from './modals/AuditLogsModal'
import { ExportModal } from './modals/ExportModal'
import { AnalyticsModal } from './modals/AnalyticsModal'
import { FilePreviewModal } from './modals/FilePreviewModal'
import { AdvancedSearchPanel } from './modals/AdvancedSearchPanel'

// Context Menus
import { ContextMenu } from './ContextMenu'
import { FileContextMenu } from './FileContextMenu'
import { FolderContextMenu } from './FolderContextMenu'
import { DocumentContextMenu } from './DocumentContextMenu'

// Types
import type { 
  ViewMode, SortField, SortDirection, FilterType, ContextMenuState,
  DeleteTarget, RenameTarget, MoveTarget, StealthLabelModal as StealthLabelModalType,
  SearchFilters, FileTag, VaultFile, VaultFolder
} from './types'
import type { Document, DocumentType } from '@/stores/docsStore'
import { sortFiles } from './helpers'

export function VaultWorkspace() {
  // Authentication hook
  const auth = useVaultAuth()
  
  // Workspace hook (files, folders, navigation)
  const workspace = useVaultWorkspace()
  
  // File operations hook
  const fileOps = useFileOperations(
    auth.currentVaultMode,
    auth.vaultPassphrase,
    workspace.currentFolderPath
  )
  
  // Selection hook
  const selection = useSelection()
  
  // Drag-drop hook
  const dragDrop = useDragDrop()
  
  // Auto-lock hook
  useAutoLock(auth.vaultUnlocked, auth.lockVault)
  
  // WebSocket hook
  const { wsConnected, realtimeNotifications } = useWebSocket(
    auth.vaultUnlocked,
    auth.currentVaultMode,
    workspace.fetchFoldersAndFiles
  )

  // Vault documents store
  const {
    getVaultDocuments,
    setActiveDocument,
    setWorkspaceView,
    createDocument,
    deleteDocument,
    removeFromVault,
    updateDocument
  } = useDocsStore()
  
  const vaultDocs = getVaultDocuments()

  // UI state
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<FilterType>('all')
  const [sortField, setSortField] = useState<SortField>('name')
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc')
  const [showFilters, setShowFilters] = useState(false)
  const [showCreateMenu, setShowCreateMenu] = useState(false)

  // Modal states
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget | null>(null)
  const [showRenameModal, setShowRenameModal] = useState(false)
  const [renameTarget, setRenameTarget] = useState<RenameTarget | null>(null)
  const [newName, setNewName] = useState('')
  const [showMoveModal, setShowMoveModal] = useState(false)
  const [moveTarget, setMoveTarget] = useState<MoveTarget | null>(null)
  const [showNewFolderModal, setShowNewFolderModal] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [showTagModal, setShowTagModal] = useState(false)
  const [tagModalFile, setTagModalFile] = useState<VaultFile | null>(null)
  const [showStealthLabelModal, setShowStealthLabelModal] = useState(false)
  const [stealthLabelModalData, setStealthLabelModalData] = useState<StealthLabelModalType | null>(null)
  const [showStorageModal, setShowStorageModal] = useState(false)
  const [showTrashModal, setShowTrashModal] = useState(false)
  const [showShareModal, setShowShareModal] = useState(false)
  const [showVersionsModal, setShowVersionsModal] = useState(false)
  const [showCommentsModal, setShowCommentsModal] = useState(false)
  const [showPinnedModal, setShowPinnedModal] = useState(false)
  const [showAuditLogsModal, setShowAuditLogsModal] = useState(false)
  const [showExportModal, setShowExportModal] = useState(false)
  const [showAnalyticsModal, setShowAnalyticsModal] = useState(false)
  const [showPreviewModal, setShowPreviewModal] = useState(false)
  const [showAdvancedSearch, setShowAdvancedSearch] = useState(false)

  // Context menu state
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null)

  // File features state
  const [favoriteFiles, setFavoriteFiles] = useState<Set<string>>(new Set())
  const [fileTags, setFileTags] = useState<Map<string, FileTag[]>>(new Map())

  // Fetch folders and files when vault unlocked
  useEffect(() => {
    if (auth.vaultUnlocked) {
      workspace.fetchFoldersAndFiles()
      loadFavorites()
    }
  }, [auth.vaultUnlocked, workspace.currentFolderPath, auth.currentVaultMode])

  // Close context menu on click
  useEffect(() => {
    const handleClick = () => setContextMenu(null)
    if (contextMenu) {
      document.addEventListener('click', handleClick)
      return () => document.removeEventListener('click', handleClick)
    }
  }, [contextMenu])

  // Load favorites
  const loadFavorites = async () => {
    try {
      const response = await axios.get('/api/v1/vault/favorites', {
        params: { vault_type: auth.currentVaultMode }
      })
      setFavoriteFiles(new Set(response.data.favorites))
    } catch (error) {
      console.error('Failed to load favorites:', error)
    }
  }

  // Favorite toggle
  const handleToggleFavorite = async (fileId: string) => {
    const newFavorites = new Set(favoriteFiles)
    try {
      if (newFavorites.has(fileId)) {
        await axios.delete(`/api/v1/vault/files/${fileId}/favorite`, {
          params: { vault_type: auth.currentVaultMode }
        })
        newFavorites.delete(fileId)
        toast.success('Removed from favorites')
      } else {
        const formData = new FormData()
        formData.append('vault_type', auth.currentVaultMode)
        await axios.post(`/api/v1/vault/files/${fileId}/favorite`, formData)
        newFavorites.add(fileId)
        toast.success('Added to favorites')
      }
      setFavoriteFiles(newFavorites)
    } catch (error: any) {
      toast.error('Failed to update favorites')
    }
  }

  // Tag handlers
  const handleOpenTagModal = (file: VaultFile) => {
    setTagModalFile(file)
    setShowTagModal(true)
    loadFileTags(file.id)
  }

  const loadFileTags = async (fileId: string) => {
    try {
      const response = await axios.get(`/api/v1/vault/files/${fileId}/tags`, {
        params: { vault_type: auth.currentVaultMode }
      })
      const newTags = new Map(fileTags)
      newTags.set(fileId, response.data.tags)
      setFileTags(newTags)
    } catch (error) {
      console.error('Failed to load tags:', error)
    }
  }

  const handleAddTag = async (tagName: string, tagColor: string) => {
    if (!tagModalFile) return
    try {
      const formData = new FormData()
      formData.append('vault_type', auth.currentVaultMode)
      formData.append('tag_name', tagName)
      formData.append('tag_color', tagColor)
      await axios.post(`/api/v1/vault/files/${tagModalFile.id}/tags`, formData)
      toast.success('Tag added')
      loadFileTags(tagModalFile.id)
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to add tag')
    }
  }

  const handleRemoveTag = async (tagName: string) => {
    if (!tagModalFile) return
    try {
      await axios.delete(`/api/v1/vault/files/${tagModalFile.id}/tags/${tagName}`, {
        params: { vault_type: auth.currentVaultMode }
      })
      toast.success('Tag removed')
      loadFileTags(tagModalFile.id)
    } catch (error: any) {
      toast.error('Failed to remove tag')
    }
  }

  // Folder operations
  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) {
      toast.error('Please enter a folder name')
      return
    }
    try {
      const formData = new FormData()
      formData.append('folder_name', newFolderName.trim())
      formData.append('vault_type', auth.currentVaultMode)
      formData.append('parent_path', workspace.currentFolderPath)
      await axios.post('/api/v1/vault/folders', formData)
      toast.success('Folder created successfully')
      setShowNewFolderModal(false)
      setNewFolderName('')
      workspace.fetchFoldersAndFiles()
    } catch (error: any) {
      console.error('Folder creation error:', error)
      toast.error(error.response?.data?.detail || 'Failed to create folder')
    }
  }

  // Delete handlers
  const confirmDelete = (type: 'file' | 'folder', item: any) => {
    setDeleteTarget({
      type,
      id: item.id,
      name: type === 'file' ? item.filename : item.folder_name,
      path: type === 'folder' ? item.folder_path : undefined
    })
    setShowDeleteModal(true)
    setContextMenu(null)
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      if (deleteTarget.type === 'file') {
        await axios.delete(`/api/v1/vault/files/${deleteTarget.id}`, {
          params: { vault_type: auth.currentVaultMode }
        })
        toast.success('File deleted successfully')
      } else {
        await axios.delete('/api/v1/vault/folders', {
          params: {
            folder_path: deleteTarget.path,
            vault_type: auth.currentVaultMode
          }
        })
        toast.success('Folder deleted successfully')
        if (deleteTarget.path === workspace.currentFolderPath) {
          workspace.navigateUp()
        }
      }
      workspace.fetchFoldersAndFiles()
      setShowDeleteModal(false)
      setDeleteTarget(null)
    } catch (error: any) {
      console.error('Delete error:', error)
      toast.error(error.response?.data?.detail || 'Failed to delete')
    }
  }

  // Rename handlers
  const startRename = (type: 'file' | 'folder', item: any) => {
    setRenameTarget({
      type,
      id: item.id,
      currentName: type === 'file' ? item.filename : item.folder_name,
      path: type === 'folder' ? item.folder_path : undefined
    })
    setNewName(type === 'file' ? item.filename : item.folder_name)
    setShowRenameModal(true)
    setContextMenu(null)
  }

  const handleRename = async (newName: string) => {
    if (!renameTarget || !newName.trim()) return
    try {
      if (renameTarget.type === 'file') {
        await axios.put(`/api/v1/vault/files/${renameTarget.id}/rename`, null, {
          params: {
            new_filename: newName.trim(),
            vault_type: auth.currentVaultMode
          }
        })
        toast.success('File renamed successfully')
      } else {
        await axios.put('/api/v1/vault/folders/rename', null, {
          params: {
            old_path: renameTarget.path,
            new_name: newName.trim(),
            vault_type: auth.currentVaultMode
          }
        })
        toast.success('Folder renamed successfully')
      }
      workspace.fetchFoldersAndFiles()
      setShowRenameModal(false)
      setRenameTarget(null)
      setNewName('')
    } catch (error: any) {
      console.error('Rename error:', error)
      toast.error(error.response?.data?.detail || 'Failed to rename')
    }
  }

  // Move handlers
  const startMove = (file: VaultFile) => {
    setMoveTarget({
      id: file.id,
      filename: file.filename,
      currentPath: file.folder_path
    })
    setShowMoveModal(true)
    setContextMenu(null)
  }

  const handleMove = async (newPath: string) => {
    if (!moveTarget) return
    try {
      await axios.put(`/api/v1/vault/files/${moveTarget.id}/move`, null, {
        params: {
          new_folder_path: newPath,
          vault_type: auth.currentVaultMode
        }
      })
      toast.success('File moved successfully')
      workspace.fetchFoldersAndFiles()
      setShowMoveModal(false)
      setMoveTarget(null)
    } catch (error: any) {
      console.error('Move error:', error)
      toast.error(error.response?.data?.detail || 'Failed to move file')
    }
  }

  // Folder drag-drop
  const handleFolderDrop = async (e: React.DragEvent, targetFolderPath: string) => {
    e.preventDefault()
    dragDrop.setDropTargetFolder(null)
    if (!dragDrop.draggedFile) return
    if (dragDrop.draggedFile.folder_path === targetFolderPath) {
      toast.info('File is already in this folder')
      return
    }
    try {
      const formData = new FormData()
      formData.append('vault_type', auth.currentVaultMode)
      formData.append('new_folder_path', targetFolderPath)
      await axios.put(`/api/v1/vault/files/${dragDrop.draggedFile.id}/move`, formData)
      toast.success(`Moved ${dragDrop.draggedFile.filename} to ${targetFolderPath}`)
      dragDrop.setDraggedFile(null)
      workspace.fetchFoldersAndFiles()
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to move file')
    }
  }

  // File drop handler (for upload)
  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault()
    dragDrop.setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      fileOps.handleFileUpload(e.dataTransfer.files, workspace.fetchFoldersAndFiles)
    }
  }

  // Preview handler
  const handlePreviewFile = async (file: VaultFile) => {
    // Preview implementation would go here
    toast.info('Preview feature - implementation needed')
  }

  // Bulk operations
  const handleBulkDelete = async () => {
    if (selection.selectedFiles.size === 0) return
    try {
      await Promise.all(
        Array.from(selection.selectedFiles).map(fileId =>
          axios.delete(`/api/v1/vault/files/${fileId}`, {
            params: { vault_type: auth.currentVaultMode }
          })
        )
      )
      toast.success(`Deleted ${selection.selectedFiles.size} file(s)`)
      workspace.fetchFoldersAndFiles()
      selection.deselectAll()
      selection.setIsMultiSelectMode(false)
    } catch (error: any) {
      console.error('Bulk delete error:', error)
      toast.error('Failed to delete some files')
    }
  }

  const handleBulkDownload = async () => {
    if (selection.selectedFiles.size === 0) return
    toast.loading('Downloading files...', { id: 'bulk-download' })
    try {
      for (const fileId of Array.from(selection.selectedFiles)) {
        const file = workspace.vaultFiles.find(f => f.id === fileId)
        if (file) {
          await fileOps.handleDownloadFile(file)
        }
      }
      toast.success(`Downloaded ${selection.selectedFiles.size} file(s)`, { id: 'bulk-download' })
    } catch (error: any) {
      console.error('Bulk download error:', error)
      toast.error('Failed to download some files', { id: 'bulk-download' })
    }
  }

  // Document handlers
  const handleOpenDocument = async (doc: Document) => {
    if (doc.security_level === 'encrypted') {
      if (!auth.vaultPassphrase) {
        toast.error('Vault passphrase not available. Please unlock vault again.')
        return
      }
      try {
        toast.loading('Decrypting document...', { id: 'decrypt' })
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
        const decryptedString = await decryptDocument(encryptedDoc, auth.vaultPassphrase)
        let decryptedContent
        try {
          decryptedContent = JSON.parse(decryptedString)
        } catch {
          decryptedContent = decryptedString
        }
        updateDocument(doc.id, {
          content: decryptedContent,
          security_level: 'standard',
        })
        toast.success('Document decrypted and opened', { id: 'decrypt' })
        setActiveDocument(doc.id)
        setWorkspaceView('docs')
      } catch (error) {
        console.error('Decryption error:', error)
        toast.error('Failed to decrypt document. Incorrect passphrase?', { id: 'decrypt' })
      }
    } else {
      setActiveDocument(doc.id)
      setWorkspaceView('docs')
      toast.success('Document opened')
    }
  }

  const handleCreateDocument = (type: DocumentType) => {
    const doc = createDocument(type)
    setShowCreateMenu(false)
    toast.success(`Secure ${type} created and encrypted`)
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

  const handleSetStealthLabel = (docId: string, currentLabel: string, realTitle: string) => {
    setStealthLabelModalData({ docId, currentLabel })
    setShowStealthLabelModal(true)
    setContextMenu(null)
  }

  const handleSaveStealthLabel = (label: string) => {
    if (stealthLabelModalData) {
      updateDocument(stealthLabelModalData.docId, {
        stealth_label: label.trim() || undefined
      })
      toast.success(label.trim() ? 'Stealth label set' : 'Stealth label removed')
      setShowStealthLabelModal(false)
      setStealthLabelModalData(null)
    }
  }

  // Sort handler
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('asc')
    }
  }

  // Locked State - Show Authentication
  if (!auth.vaultUnlocked) {
    return (
      <div className="h-full flex items-center justify-center bg-gradient-to-br from-amber-50 to-orange-50 dark:from-gray-900 dark:to-gray-800">
        <div className="max-w-md w-full mx-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl p-8">
            <div className="text-center mb-6">
              <div className="w-20 h-20 bg-amber-100 dark:bg-amber-900/30 rounded-full flex items-center justify-center mx-auto mb-4 relative">
                <Lock className="w-10 h-10 text-amber-600 dark:text-amber-400" />
                {auth.biometricAvailable && auth.requireTouchID && (
                  <Fingerprint className="absolute -top-2 -right-2 w-8 h-8 text-blue-600 dark:text-blue-400" />
                )}
              </div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                Secure Vault
              </h2>
              <p className="text-gray-600 dark:text-gray-400 text-sm">
                {auth.requireTouchID ? 'Touch ID and password required' : 'Password required'}
              </p>
            </div>

            {auth.authError && (
              <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-2">
                <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0" />
                <p className="text-sm text-red-700 dark:text-red-300">{auth.authError}</p>
              </div>
            )}

            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Vault Password
              </label>
              <div className="relative">
                <input
                  type={auth.showPassword ? 'text' : 'password'}
                  value={auth.password}
                  onChange={(e) => auth.setPassword(e.target.value)}
                  onKeyPress={auth.handleKeyPress}
                  placeholder="Enter your password"
                  disabled={auth.isAuthenticating}
                  className="w-full px-4 py-3 pr-12 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-amber-500 focus:border-transparent disabled:opacity-50"
                />
                <button
                  type="button"
                  onClick={() => auth.setShowPassword(!auth.showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  {auth.showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <button
              onClick={auth.handleUnlock}
              disabled={auth.isAuthenticating || !auth.password}
              className="w-full py-3 bg-amber-600 hover:bg-amber-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {auth.biometricAvailable && <Fingerprint className="w-5 h-5" />}
              {auth.isAuthenticating ? 'Authenticating...' : 'Unlock Vault'}
            </button>

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
                {auth.currentVaultMode === 'decoy' ? 'Standard Mode' : 'Protected Mode'}
              </p>
            </div>
          </div>
          <ContextBadge size="sm" />
        </div>

        <button
          onClick={auth.lockVault}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
        >
          <Lock className="w-4 h-4" />
          Lock Vault
        </button>
      </div>

      {/* Vault Content */}
      <div
        className="flex-1 p-6 overflow-auto"
        onDrop={handleFileDrop}
        onDragOver={dragDrop.handleDragOver}
        onDragLeave={dragDrop.handleDragLeave}
      >
        <div className="max-w-6xl mx-auto">
          {/* Hidden File Input */}
          <input
            ref={fileOps.fileInputRef}
            type="file"
            multiple
            onChange={(e) => {
              if (e.target.files) {
                fileOps.handleFileUpload(e.target.files, workspace.fetchFoldersAndFiles)
              }
            }}
            className="hidden"
          />

          {/* Upload Progress */}
          {fileOps.uploadingFiles.length > 0 && (
            <div className="mb-6 space-y-2">
              {fileOps.uploadingFiles.map((upload) => (
                <div
                  key={upload.id}
                  className="flex items-center gap-3 p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg"
                >
                  <File className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                        {upload.name}
                      </p>
                      <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">
                        {upload.status === 'uploading' && `${upload.progress}%`}
                        {upload.status === 'complete' && '✓ Complete'}
                        {upload.status === 'error' && '✗ Failed'}
                      </span>
                    </div>
                    {upload.status === 'uploading' && (
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                        <div
                          className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                          style={{ width: `${upload.progress}%` }}
                        />
                      </div>
                    )}
                    {upload.status === 'error' && upload.error && (
                      <p className="text-xs text-red-600 dark:text-red-400">{upload.error}</p>
                    )}
                  </div>
                  {upload.status === 'complete' && (
                    <button
                      onClick={() => fileOps.removeUploadedFile(upload.id)}
                      className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                    >
                      <X className="w-4 h-4 text-gray-500" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Drag Overlay */}
          {dragDrop.isDragging && (
            <div className="fixed inset-0 z-40 bg-blue-500/10 backdrop-blur-sm flex items-center justify-center pointer-events-none">
              <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl p-12 border-2 border-dashed border-blue-500">
                <Upload className="w-16 h-16 text-blue-600 dark:text-blue-400 mx-auto mb-4" />
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 text-center">
                  Drop files to upload
                </p>
                <p className="text-gray-600 dark:text-gray-400 text-center mt-2">
                  Files will be encrypted and stored securely
                </p>
              </div>
            </div>
          )}

          {/* Breadcrumbs */}
          <Breadcrumbs
            currentPath={workspace.currentFolderPath}
            onNavigate={workspace.navigateToFolder}
            onNewFolder={() => setShowNewFolderModal(true)}
          />

          {/* Toolbar */}
          <Toolbar
            onUploadClick={() => fileOps.fileInputRef.current?.click()}
            isMultiSelectMode={selection.isMultiSelectMode}
            selectedFilesCount={selection.selectedFiles.size}
            onToggleMultiSelect={selection.toggleMultiSelectMode}
            onSelectAll={() => selection.selectAll(
              workspace.vaultFiles.map(f => f.id),
              workspace.folders.map(f => f.id)
            )}
            onDeselectAll={selection.deselectAll}
            onBulkDownload={handleBulkDownload}
            onBulkDelete={handleBulkDelete}
            onStorageClick={() => setShowStorageModal(true)}
            onTrashClick={() => setShowTrashModal(true)}
            onPinnedClick={() => setShowPinnedModal(true)}
            onAuditClick={() => setShowAuditLogsModal(true)}
            onExportClick={() => setShowExportModal(true)}
            onAnalyticsClick={() => setShowAnalyticsModal(true)}
            showAdvancedSearch={showAdvancedSearch}
            onToggleAdvancedSearch={() => setShowAdvancedSearch(!showAdvancedSearch)}
            wsConnected={wsConnected}
            hasNotifications={realtimeNotifications.length > 0}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            filterType={filterType}
            onFilterChange={setFilterType}
            sortField={sortField}
            sortDirection={sortDirection}
            onSortFieldChange={handleSort}
            onToggleSortDirection={() => setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')}
            viewMode={viewMode}
            onViewModeChange={setViewMode}
          />

          {/* Folders and Files Grid */}
          {(workspace.folders.length > 0 || workspace.vaultFiles.length > 0) ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <FolderGrid
                folders={workspace.folders}
                dropTargetFolder={dragDrop.dropTargetFolder}
                onFolderClick={workspace.navigateToFolder}
                onFolderContextMenu={(e, folder) => setContextMenu({
                  x: e.clientX,
                  y: e.clientY,
                  type: 'folder',
                  item: folder
                })}
                onFolderDragOver={dragDrop.handleFolderDragOver}
                onFolderDragLeave={dragDrop.handleFolderDragLeave}
                onFolderDrop={handleFolderDrop}
              />
              <FileGrid
                files={workspace.vaultFiles}
                isMultiSelectMode={selection.isMultiSelectMode}
                selectedFiles={selection.selectedFiles}
                favoriteFiles={favoriteFiles}
                fileTags={fileTags}
                currentVaultMode={auth.currentVaultMode}
                vaultPassphrase={auth.vaultPassphrase}
                onFileClick={handlePreviewFile}
                onFileContextMenu={(e, file) => setContextMenu({
                  x: e.clientX,
                  y: e.clientY,
                  type: 'file',
                  item: file
                })}
                onFileDragStart={dragDrop.handleFileDragStart}
                onFileDragEnd={dragDrop.handleFileDragEnd}
                onToggleSelection={selection.toggleFileSelection}
                onToggleFavorite={handleToggleFavorite}
                onPreviewFile={handlePreviewFile}
                onDownloadFile={fileOps.handleDownloadFile}
                onOpenTagModal={handleOpenTagModal}
              />
            </div>
          ) : (
            <EmptyState
              onUploadClick={() => fileOps.fileInputRef.current?.click()}
              onCreateFolderClick={() => setShowNewFolderModal(true)}
            />
          )}
        </div>
      </div>

      {/* Context Menu */}
      <ContextMenu contextMenu={contextMenu} onClose={() => setContextMenu(null)}>
        {contextMenu?.type === 'file' && (
          <FileContextMenu
            onDownload={() => {
              fileOps.handleDownloadFile(contextMenu.item)
              setContextMenu(null)
            }}
            onRename={() => startRename('file', contextMenu.item)}
            onMove={() => startMove(contextMenu.item)}
            onShare={() => {
              setShowShareModal(true)
              setContextMenu(null)
            }}
            onVersionHistory={() => {
              setShowVersionsModal(true)
              setContextMenu(null)
            }}
            onComments={() => {
              setShowCommentsModal(true)
              setContextMenu(null)
            }}
            onDelete={() => confirmDelete('file', contextMenu.item)}
          />
        )}
        {contextMenu?.type === 'folder' && (
          <FolderContextMenu
            onRename={() => startRename('folder', contextMenu.item)}
            onDelete={() => confirmDelete('folder', contextMenu.item)}
          />
        )}
      </ContextMenu>

      {/* Modals */}
      <DeleteConfirmModal
        isOpen={showDeleteModal}
        deleteTarget={deleteTarget}
        onConfirm={handleDelete}
        onClose={() => {
          setShowDeleteModal(false)
          setDeleteTarget(null)
        }}
      />

      <RenameModal
        isOpen={showRenameModal}
        renameTarget={renameTarget}
        onConfirm={handleRename}
        onClose={() => {
          setShowRenameModal(false)
          setRenameTarget(null)
          setNewName('')
        }}
      />

      <NewFolderModal
        isOpen={showNewFolderModal}
        onConfirm={handleCreateFolder}
        onClose={() => {
          setShowNewFolderModal(false)
          setNewFolderName('')
        }}
      />

      <MoveFileModal
        isOpen={showMoveModal}
        moveTarget={moveTarget}
        folders={workspace.folders}
        onMove={handleMove}
        onClose={() => {
          setShowMoveModal(false)
          setMoveTarget(null)
        }}
      />

      <TagManagementModal
        isOpen={showTagModal}
        file={tagModalFile}
        tags={tagModalFile ? (fileTags.get(tagModalFile.id) || []) : []}
        onAddTag={handleAddTag}
        onRemoveTag={handleRemoveTag}
        onClose={() => {
          setShowTagModal(false)
          setTagModalFile(null)
        }}
      />

      <StealthLabelModal
        isOpen={showStealthLabelModal}
        docId={stealthLabelModalData?.docId || null}
        currentLabel={stealthLabelModalData?.currentLabel || ''}
        realTitle={vaultDocs.find(d => d.id === stealthLabelModalData?.docId)?.title || ''}
        onSave={handleSaveStealthLabel}
        onClose={() => {
          setShowStealthLabelModal(false)
          setStealthLabelModalData(null)
        }}
      />

      <StorageDashboardModal isOpen={showStorageModal} onClose={() => setShowStorageModal(false)} />
      <TrashBinModal isOpen={showTrashModal} onClose={() => setShowTrashModal(false)} />
      <ShareDialogModal isOpen={showShareModal} onClose={() => setShowShareModal(false)} />
      <VersionHistoryModal isOpen={showVersionsModal} onClose={() => setShowVersionsModal(false)} />
      <CommentsModal isOpen={showCommentsModal} onClose={() => setShowCommentsModal(false)} />
      <PinnedFilesModal isOpen={showPinnedModal} onClose={() => setShowPinnedModal(false)} />
      <AuditLogsModal isOpen={showAuditLogsModal} onClose={() => setShowAuditLogsModal(false)} />
      <ExportModal isOpen={showExportModal} onClose={() => setShowExportModal(false)} />
      <AnalyticsModal isOpen={showAnalyticsModal} onClose={() => setShowAnalyticsModal(false)} />
      <FilePreviewModal isOpen={showPreviewModal} onClose={() => setShowPreviewModal(false)} />
      <AdvancedSearchPanel isOpen={showAdvancedSearch} onClose={() => setShowAdvancedSearch(false)} />
    </div>
  )
}
