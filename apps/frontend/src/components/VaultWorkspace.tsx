/**
 * Vault Workspace
 *
 * Secure file browser (Proton Drive style) with Touch ID + Password authentication
 */

import { useState, useEffect, useRef } from 'react'
import { useDocsStore } from '@/stores/docsStore'
import { Lock, Fingerprint, AlertTriangle, FileText, Table2, Lightbulb, Eye, EyeOff, Grid3x3, List, Search, Plus, MoreVertical, Shield, Clock, HardDrive, FolderOpen, Filter, SlidersHorizontal, ArrowUpDown, Upload, X, File, Folder, FolderPlus, ChevronRight, Home, Image, Video, Music, FileArchive, Code, FileJson, Download, Edit2, Trash2, FolderInput, ZoomIn, ZoomOut, Maximize, Minimize, Star, Tag, History, Play, Pause, Volume2, SkipBack, SkipForward, CheckSquare, Square, Check, Move, Share2, MessageSquare, Pin, PinOff, GitBranch, RotateCcw, Send, Calendar, Link2, Copy, Settings, FileText as FileTextIcon, Palette, Archive, Activity, Database, BarChart3, TrendingUp, Bell, Wifi, WifiOff } from 'lucide-react'
import { authenticateBiometric, isBiometricAvailable } from '@/lib/biometricAuth'
import toast from 'react-hot-toast'
import type { Document, DocumentType } from '@/stores/docsStore'
import { decryptDocument } from '@/lib/encryption'
import axios from 'axios'
import { vaultWebSocket } from '@/lib/websocketClient'
import type { FileEvent } from '@/lib/websocketClient'

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
  const [filterType, setFilterType] = useState<'all' | DocumentType>('all')
  const [sortBy, setSortBy] = useState<'name' | 'created' | 'modified'>('modified')
  const [showFilters, setShowFilters] = useState(false)
  const [stealthLabelModal, setStealthLabelModal] = useState<{ docId: string; currentLabel: string } | null>(null)
  const [stealthLabelInput, setStealthLabelInput] = useState('')

  // File upload state
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploadingFiles, setUploadingFiles] = useState<Array<{
    id: string
    name: string
    size: number
    progress: number
    status: 'uploading' | 'complete' | 'error'
    error?: string
  }>>([])
  const [isDragging, setIsDragging] = useState(false)

  // Folder navigation state
  const [currentFolderPath, setCurrentFolderPath] = useState('/')
  const [folders, setFolders] = useState<Array<{
    id: string
    folder_name: string
    folder_path: string
    parent_path: string
    created_at: string
  }>>([])
  const [vaultFiles, setVaultFiles] = useState<Array<{
    id: string
    filename: string
    file_size: number
    mime_type: string
    folder_path: string
    created_at: string
  }>>([])
  const [showNewFolderModal, setShowNewFolderModal] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')

  // Context menu state
  const [contextMenu, setContextMenu] = useState<{
    x: number
    y: number
    type: 'file' | 'folder'
    item: any
  } | null>(null)

  // Modal states
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<{
    type: 'file' | 'folder'
    id?: string
    name: string
    path?: string
  } | null>(null)

  const [showRenameModal, setShowRenameModal] = useState(false)
  const [renameTarget, setRenameTarget] = useState<{
    type: 'file' | 'folder'
    id?: string
    currentName: string
    path?: string
  } | null>(null)
  const [newName, setNewName] = useState('')

  const [showMoveModal, setShowMoveModal] = useState(false)
  const [moveTarget, setMoveTarget] = useState<{
    id: string
    filename: string
    currentPath: string
  } | null>(null)

  // File preview state
  const [showPreviewModal, setShowPreviewModal] = useState(false)
  const [previewFile, setPreviewFile] = useState<any | null>(null)
  const [previewContent, setPreviewContent] = useState<string | null>(null)
  const [previewZoom, setPreviewZoom] = useState(1)

  // Multi-select state
  const [isMultiSelectMode, setIsMultiSelectMode] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set())
  const [selectedFolders, setSelectedFolders] = useState<Set<string>>(new Set())

  // Favorites and tags
  const [favoriteFiles, setFavoriteFiles] = useState<Set<string>>(new Set())
  const [fileTags, setFileTags] = useState<Map<string, Array<{tag_name: string, tag_color: string}>>>(new Map())

  // Tag management modal
  const [showTagModal, setShowTagModal] = useState(false)
  const [tagModalFile, setTagModalFile] = useState<any | null>(null)
  const [newTagName, setNewTagName] = useState('')
  const [newTagColor, setNewTagColor] = useState('#3B82F6')

  // Sort state
  const [sortField, setSortField] = useState<'name' | 'date' | 'size' | 'type'>('name')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')

  // Storage dashboard
  const [showStorageModal, setShowStorageModal] = useState(false)
  const [storageStats, setStorageStats] = useState<any | null>(null)

  // Drag and drop
  const [draggedFile, setDraggedFile] = useState<any | null>(null)
  const [dropTargetFolder, setDropTargetFolder] = useState<string | null>(null)

  // Auto-lock timer
  const inactivityTimerRef = useRef<NodeJS.Timeout | null>(null)

  // Day 4: File Versioning
  const [showVersionsModal, setShowVersionsModal] = useState(false)
  const [versionsFile, setVersionsFile] = useState<any | null>(null)
  const [fileVersions, setFileVersions] = useState<Array<any>>([])

  // Day 4: Trash/Recycle Bin
  const [showTrashModal, setShowTrashModal] = useState(false)
  const [trashFiles, setTrashFiles] = useState<Array<any>>([])

  // Day 4: Advanced Search
  const [showAdvancedSearch, setShowAdvancedSearch] = useState(false)
  const [searchFilters, setSearchFilters] = useState({
    query: '',
    mimeType: '',
    tags: [],
    dateFrom: '',
    dateTo: '',
    minSize: '',
    maxSize: '',
    folderPath: ''
  })
  const [searchResults, setSearchResults] = useState<Array<any>>([])

  // Day 4: File Sharing
  const [showShareModal, setShowShareModal] = useState(false)
  const [shareFile, setShareFile] = useState<any | null>(null)
  const [shareLinks, setShareLinks] = useState<Array<any>>([])
  const [sharePassword, setSharePassword] = useState('')
  const [shareExpiry, setShareExpiry] = useState('')
  const [shareMaxDownloads, setShareMaxDownloads] = useState('')

  // Day 4: Comments
  const [showCommentsModal, setShowCommentsModal] = useState(false)
  const [commentsFile, setCommentsFile] = useState<any | null>(null)
  const [fileComments, setFileComments] = useState<Array<any>>([])
  const [newComment, setNewComment] = useState('')

  // Day 4: Audit Logs
  const [showAuditLogs, setShowAuditLogs] = useState(false)
  const [auditLogs, setAuditLogs] = useState<Array<any>>([])

  // Day 4: Pinned Files
  const [pinnedFiles, setPinnedFiles] = useState<Array<any>>([])

  // Day 4: Folder Colors
  const [folderColors, setFolderColors] = useState<Map<string, string>>(new Map())
  const [showColorPicker, setShowColorPicker] = useState(false)
  const [colorPickerFolder, setColorPickerFolder] = useState<any | null>(null)

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

  // Get file type icon based on MIME type
  const getFileIcon = (mimeType: string) => {
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

  // Get file icon color based on MIME type
  const getFileIconColor = (mimeType: string) => {
    if (mimeType.startsWith('image/')) return 'text-purple-600 dark:text-purple-400 bg-purple-100 dark:bg-purple-900/30'
    if (mimeType.startsWith('video/')) return 'text-pink-600 dark:text-pink-400 bg-pink-100 dark:bg-pink-900/30'
    if (mimeType.startsWith('audio/')) return 'text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/30'
    if (mimeType === 'application/pdf') return 'text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30'
    if (mimeType.includes('zip') || mimeType.includes('archive')) return 'text-yellow-600 dark:text-yellow-400 bg-yellow-100 dark:bg-yellow-900/30'
    if (mimeType.includes('code') || mimeType.includes('javascript') || mimeType.includes('python')) return 'text-indigo-600 dark:text-indigo-400 bg-indigo-100 dark:bg-indigo-900/30'
    return 'text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-800'
  }

  // Format bytes to human-readable size
  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
  }

  // Download file
  const handleDownloadFile = async (file: typeof vaultFiles[0]) => {
    try {
      const response = await axios.get(`/api/v1/vault/files/${file.id}/download`, {
        params: {
          vault_type: currentVaultMode,
          vault_passphrase: vaultPassphrase
        },
        responseType: 'blob'
      })

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', file.filename)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)

      toast.success('File downloaded successfully')
    } catch (error: any) {
      console.error('Download error:', error)
      toast.error(error.response?.data?.detail || 'Failed to download file')
    }
  }

  // Context menu handlers
  const handleFileContextMenu = (e: React.MouseEvent, file: typeof vaultFiles[0]) => {
    e.preventDefault()
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      type: 'file',
      item: file
    })
  }

  const handleFolderContextMenu = (e: React.MouseEvent, folder: typeof folders[0]) => {
    e.preventDefault()
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      type: 'folder',
      item: folder
    })
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
          params: { vault_type: currentVaultMode }
        })
        toast.success('File deleted successfully')
      } else {
        await axios.delete('/api/v1/vault/folders', {
          params: {
            folder_path: deleteTarget.path,
            vault_type: currentVaultMode
          }
        })
        toast.success('Folder deleted successfully')

        // Navigate up if we deleted the current folder
        if (deleteTarget.path === currentFolderPath) {
          navigateUp()
        }
      }

      fetchFoldersAndFiles()
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

  const handleRename = async () => {
    if (!renameTarget || !newName.trim()) return

    try {
      if (renameTarget.type === 'file') {
        await axios.put(`/api/v1/vault/files/${renameTarget.id}/rename`, null, {
          params: {
            new_filename: newName.trim(),
            vault_type: currentVaultMode
          }
        })
        toast.success('File renamed successfully')
      } else {
        await axios.put('/api/v1/vault/folders/rename', null, {
          params: {
            old_path: renameTarget.path,
            new_name: newName.trim(),
            vault_type: currentVaultMode
          }
        })
        toast.success('Folder renamed successfully')
      }

      fetchFoldersAndFiles()
      setShowRenameModal(false)
      setRenameTarget(null)
      setNewName('')
    } catch (error: any) {
      console.error('Rename error:', error)
      toast.error(error.response?.data?.detail || 'Failed to rename')
    }
  }

  // Move handlers
  const startMove = (file: typeof vaultFiles[0]) => {
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
          vault_type: currentVaultMode
        }
      })

      toast.success('File moved successfully')
      fetchFoldersAndFiles()
      setShowMoveModal(false)
      setMoveTarget(null)
    } catch (error: any) {
      console.error('Move error:', error)
      toast.error(error.response?.data?.detail || 'Failed to move file')
    }
  }

  // File preview handler
  const handlePreviewFile = async (file: any) => {
    setPreviewFile(file)
    setShowPreviewModal(true)
    setPreviewZoom(1)

    try {
      const response = await axios.get(`/api/v1/vault/files/${file.id}/download`, {
        params: {
          vault_type: currentVaultMode,
          vault_passphrase: vaultPassphrase
        },
        responseType: 'blob'
      })

      const mimeType = file.mime_type
      if (mimeType.startsWith('image/')) {
        const url = URL.createObjectURL(response.data)
        setPreviewContent(url)
      } else if (mimeType.startsWith('text/') || mimeType === 'application/json') {
        const text = await response.data.text()
        setPreviewContent(text)
      } else if (mimeType === 'application/pdf') {
        const url = URL.createObjectURL(response.data)
        setPreviewContent(url)
      } else if (mimeType.startsWith('audio/') || mimeType.startsWith('video/')) {
        const url = URL.createObjectURL(response.data)
        setPreviewContent(url)
      } else {
        toast.error('Preview not available for this file type')
        setShowPreviewModal(false)
      }
    } catch (error: any) {
      console.error('Preview error:', error)
      toast.error('Failed to load file preview')
      setShowPreviewModal(false)
    }
  }

  // Multi-select handlers
  const toggleMultiSelectMode = () => {
    setIsMultiSelectMode(!isMultiSelectMode)
    setSelectedFiles(new Set())
    setSelectedFolders(new Set())
  }

  const toggleFileSelection = (fileId: string) => {
    const newSelection = new Set(selectedFiles)
    if (newSelection.has(fileId)) {
      newSelection.delete(fileId)
    } else {
      newSelection.add(fileId)
    }
    setSelectedFiles(newSelection)
  }

  const selectAll = () => {
    setSelectedFiles(new Set(vaultFiles.map(f => f.id)))
    setSelectedFolders(new Set(folders.map(f => f.id)))
  }

  const deselectAll = () => {
    setSelectedFiles(new Set())
    setSelectedFolders(new Set())
  }

  // Bulk operations
  const handleBulkDelete = async () => {
    if (selectedFiles.size === 0) return

    try {
      await Promise.all(
        Array.from(selectedFiles).map(fileId =>
          axios.delete(`/api/v1/vault/files/${fileId}`, {
            params: { vault_type: currentVaultMode }
          })
        )
      )

      toast.success(`Deleted ${selectedFiles.size} file(s)`)
      fetchFoldersAndFiles()
      deselectAll()
      setIsMultiSelectMode(false)
    } catch (error: any) {
      console.error('Bulk delete error:', error)
      toast.error('Failed to delete some files')
    }
  }

  const handleBulkDownload = async () => {
    if (selectedFiles.size === 0) return

    toast.loading('Downloading files...', { id: 'bulk-download' })

    try {
      for (const fileId of Array.from(selectedFiles)) {
        const file = vaultFiles.find(f => f.id === fileId)
        if (file) {
          await handleDownloadFile(file)
        }
      }

      toast.success(`Downloaded ${selectedFiles.size} file(s)`, { id: 'bulk-download' })
    } catch (error: any) {
      console.error('Bulk download error:', error)
      toast.error('Failed to download some files', { id: 'bulk-download' })
    }
  }

  // Favorites handler
  const toggleFavorite = async (fileId: string) => {
    const newFavorites = new Set(favoriteFiles)
    try {
      if (newFavorites.has(fileId)) {
        await axios.delete(`/api/v1/vault/files/${fileId}/favorite`, {
          params: { vault_type: currentVaultMode }
        })
        newFavorites.delete(fileId)
        toast.success('Removed from favorites')
      } else {
        const formData = new FormData()
        formData.append('vault_type', currentVaultMode)
        await axios.post(`/api/v1/vault/files/${fileId}/favorite`, formData)
        newFavorites.add(fileId)
        toast.success('Added to favorites')
      }
      setFavoriteFiles(newFavorites)
    } catch (error: any) {
      toast.error('Failed to update favorites')
      console.error('Failed to update favorites:', error)
    }
  }

  // Tag management handlers
  const openTagModal = (file: any) => {
    setTagModalFile(file)
    setShowTagModal(true)
    setNewTagName('')
    setNewTagColor('#3B82F6')
    loadFileTags(file.id)
  }

  const loadFileTags = async (fileId: string) => {
    try {
      const response = await axios.get(`/api/v1/vault/files/${fileId}/tags`, {
        params: { vault_type: currentVaultMode }
      })
      const newTags = new Map(fileTags)
      newTags.set(fileId, response.data.tags)
      setFileTags(newTags)
    } catch (error) {
      console.error('Failed to load tags:', error)
    }
  }

  const addTag = async () => {
    if (!newTagName.trim() || !tagModalFile) return

    try {
      const formData = new FormData()
      formData.append('vault_type', currentVaultMode)
      formData.append('tag_name', newTagName.trim())
      formData.append('tag_color', newTagColor)

      await axios.post(`/api/v1/vault/files/${tagModalFile.id}/tags`, formData)

      toast.success('Tag added')
      setNewTagName('')
      loadFileTags(tagModalFile.id)
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to add tag')
      console.error('Failed to add tag:', error)
    }
  }

  const removeTag = async (fileId: string, tagName: string) => {
    try {
      await axios.delete(`/api/v1/vault/files/${fileId}/tags/${tagName}`, {
        params: { vault_type: currentVaultMode }
      })

      toast.success('Tag removed')
      loadFileTags(fileId)
    } catch (error: any) {
      toast.error('Failed to remove tag')
      console.error('Failed to remove tag:', error)
    }
  }

  const loadAllFileTags = async () => {
    // Load tags for all visible files
    const fileIds = vaultFiles.map(f => f.id)
    const newTagsMap = new Map(fileTags)

    for (const fileId of fileIds) {
      try {
        const response = await axios.get(`/api/v1/vault/files/${fileId}/tags`, {
          params: { vault_type: currentVaultMode }
        })
        newTagsMap.set(fileId, response.data.tags)
      } catch (error) {
        // Silently fail for individual files
      }
    }

    setFileTags(newTagsMap)
  }

  // Storage statistics
  const loadStorageStats = async () => {
    try {
      const response = await axios.get('/api/v1/vault/storage-stats', {
        params: { vault_type: currentVaultMode }
      })
      setStorageStats(response.data)
    } catch (error) {
      console.error('Failed to load storage stats:', error)
      toast.error('Failed to load storage statistics')
    }
  }

  const openStorageModal = () => {
    setShowStorageModal(true)
    loadStorageStats()
  }

  // Drag and drop handlers
  const handleFileDragStart = (e: React.DragEvent, file: any) => {
    setDraggedFile(file)
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', file.id)
  }

  const handleFileDragEnd = () => {
    setDraggedFile(null)
    setDropTargetFolder(null)
  }

  const handleFolderDragOver = (e: React.DragEvent, folderPath: string) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDropTargetFolder(folderPath)
  }

  const handleFolderDragLeave = () => {
    setDropTargetFolder(null)
  }

  const handleFolderDrop = async (e: React.DragEvent, targetFolderPath: string) => {
    e.preventDefault()
    setDropTargetFolder(null)

    if (!draggedFile) return

    // Don't move if already in target folder
    if (draggedFile.folder_path === targetFolderPath) {
      toast.info('File is already in this folder')
      return
    }

    try {
      const formData = new FormData()
      formData.append('vault_type', currentVaultMode)
      formData.append('new_folder_path', targetFolderPath)

      await axios.put(`/api/v1/vault/files/${draggedFile.id}/move`, formData)

      toast.success(`Moved ${draggedFile.filename} to ${targetFolderPath}`)
      setDraggedFile(null)
      fetchFoldersAndFiles()
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to move file')
      console.error('Failed to move file:', error)
    }
  }

  // Sort handler
  const handleSort = (field: 'name' | 'date' | 'size' | 'type') => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('asc')
    }
  }

  const sortFiles = (files: typeof vaultFiles) => {
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

  // File upload handlers
  // Day 5: Chunked upload for large files
  const uploadLargeFile = async (file: File, uploadId: string) => {
    const CHUNK_SIZE = 5 * 1024 * 1024 // 5MB chunks
    const totalChunks = Math.ceil(file.size / CHUNK_SIZE)
    const fileId = crypto.randomUUID()

    for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
      const start = chunkIndex * CHUNK_SIZE
      const end = Math.min(start + CHUNK_SIZE, file.size)
      const chunk = file.slice(start, end)

      const formData = new FormData()
      formData.append('chunk', chunk)
      formData.append('chunk_index', chunkIndex.toString())
      formData.append('total_chunks', totalChunks.toString())
      formData.append('file_id', fileId)
      formData.append('filename', file.name)
      formData.append('vault_passphrase', vaultPassphrase || '')
      formData.append('vault_type', currentVaultMode)
      formData.append('folder_path', currentFolderPath)

      const response = await axios.post('/api/v1/vault/upload-chunk', formData, {
        onUploadProgress: (progressEvent) => {
          const chunkProgress = progressEvent.total
            ? (progressEvent.loaded / progressEvent.total) * 100
            : 0
          const totalProgress = ((chunkIndex + chunkProgress / 100) / totalChunks) * 100

          setUploadingFiles(prev => prev.map(upload =>
            upload.id === uploadId
              ? { ...upload, progress: Math.round(totalProgress) }
              : upload
          ))
        }
      })

      if (response.data.status === 'complete') {
        return response.data.file
      }
    }
  }

  const handleFileUpload = async (files: FileList | File[]) => {
    const fileArray = Array.from(files)

    // Add files to uploading queue
    const newUploads = fileArray.map(file => ({
      id: `${file.name}-${Date.now()}`,
      name: file.name,
      size: file.size,
      progress: 0,
      status: 'uploading' as const
    }))

    setUploadingFiles(prev => [...prev, ...newUploads])

    // Upload each file
    for (let i = 0; i < fileArray.length; i++) {
      const file = fileArray[i]
      const uploadId = newUploads[i].id

      try {
        const LARGE_FILE_THRESHOLD = 5 * 1024 * 1024 // 5MB

        // Use chunked upload for large files
        if (file.size > LARGE_FILE_THRESHOLD) {
          await uploadLargeFile(file, uploadId)
        } else {
          // Regular upload for small files
          const formData = new FormData()
          formData.append('file', file)
          formData.append('vault_passphrase', vaultPassphrase || '')
          formData.append('vault_type', currentVaultMode)
          formData.append('folder_path', currentFolderPath)

          await axios.post('/api/v1/vault/upload', formData, {
            headers: {
              'Content-Type': 'multipart/form-data',
            },
            onUploadProgress: (progressEvent) => {
              const percentCompleted = progressEvent.total
                ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
                : 0

              setUploadingFiles(prev => prev.map(upload =>
                upload.id === uploadId
                  ? { ...upload, progress: percentCompleted }
                  : upload
              ))
            }
          })
        }

        // Mark as complete
        setUploadingFiles(prev => prev.map(upload =>
          upload.id === uploadId
            ? { ...upload, status: 'complete', progress: 100 }
            : upload
        ))

        toast.success(`${file.name} uploaded successfully`)

        // Refresh files list
        fetchFoldersAndFiles()

        // Remove from list after 2 seconds
        setTimeout(() => {
          setUploadingFiles(prev => prev.filter(u => u.id !== uploadId))
        }, 2000)

      } catch (error: any) {
        console.error('Upload error:', error)
        setUploadingFiles(prev => prev.map(upload =>
          upload.id === uploadId
            ? {
                ...upload,
                status: 'error',
                error: error.response?.data?.message || 'Upload failed'
              }
            : upload
        ))
        toast.error(`Failed to upload ${file.name}`)
      }
    }
  }

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files)
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const removeUploadedFile = (uploadId: string) => {
    setUploadingFiles(prev => prev.filter(u => u.id !== uploadId))
  }

  // Fetch folders and files for current path
  const loadFavorites = async () => {
    try {
      const response = await axios.get('/api/v1/vault/favorites', {
        params: { vault_type: currentVaultMode }
      })
      setFavoriteFiles(new Set(response.data.favorites))
    } catch (error) {
      console.error('Failed to load favorites:', error)
    }
  }

  const fetchFoldersAndFiles = async () => {
    if (!vaultUnlocked) return

    try {
      // Fetch folders in current path
      const foldersRes = await axios.get('/api/v1/vault/folders', {
        params: {
          vault_type: currentVaultMode,
          parent_path: currentFolderPath
        }
      })
      setFolders(foldersRes.data)

      // Fetch files in current path
      const filesRes = await axios.get('/api/v1/vault/files', {
        params: {
          vault_type: currentVaultMode,
          folder_path: currentFolderPath
        }
      })
      setVaultFiles(filesRes.data)

      // Load tags for all files
      if (filesRes.data.length > 0) {
        const newTagsMap = new Map()
        for (const file of filesRes.data) {
          try {
            const tagsRes = await axios.get(`/api/v1/vault/files/${file.id}/tags`, {
              params: { vault_type: currentVaultMode }
            })
            newTagsMap.set(file.id, tagsRes.data.tags)
          } catch (error) {
            // Silently fail for individual files
          }
        }
        setFileTags(newTagsMap)
      }
    } catch (error) {
      console.error('Failed to fetch vault contents:', error)
    }
  }

  // Fetch when vault unlocked or folder changes
  useEffect(() => {
    if (vaultUnlocked) {
      fetchFoldersAndFiles()
      loadFavorites()
    }
  }, [vaultUnlocked, currentFolderPath, currentVaultMode])

  // Create new folder
  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) {
      toast.error('Please enter a folder name')
      return
    }

    try {
      const formData = new FormData()
      formData.append('folder_name', newFolderName.trim())
      formData.append('vault_type', currentVaultMode)
      formData.append('parent_path', currentFolderPath)

      await axios.post('/api/v1/vault/folders', formData)

      toast.success('Folder created successfully')
      setShowNewFolderModal(false)
      setNewFolderName('')
      fetchFoldersAndFiles()
    } catch (error: any) {
      console.error('Folder creation error:', error)
      toast.error(error.response?.data?.detail || 'Failed to create folder')
    }
  }

  // Navigate to folder
  const navigateToFolder = (folderPath: string) => {
    setCurrentFolderPath(folderPath)
  }

  // Navigate up to parent folder
  const navigateUp = () => {
    if (currentFolderPath === '/') return

    const parts = currentFolderPath.split('/').filter(Boolean)
    parts.pop()
    const parentPath = parts.length > 0 ? '/' + parts.join('/') : '/'
    setCurrentFolderPath(parentPath)
  }

  // Get breadcrumb parts
  const getBreadcrumbs = () => {
    if (currentFolderPath === '/') return [{ name: 'Root', path: '/' }]

    const parts = currentFolderPath.split('/').filter(Boolean)
    const breadcrumbs = [{ name: 'Root', path: '/' }]

    parts.forEach((part, index) => {
      const path = '/' + parts.slice(0, index + 1).join('/')
      breadcrumbs.push({ name: part, path })
    })

    return breadcrumbs
  }

  // Close context menu on click
  useEffect(() => {
    const handleClick = () => setContextMenu(null)
    if (contextMenu) {
      document.addEventListener('click', handleClick)
      return () => document.removeEventListener('click', handleClick)
    }
  }, [contextMenu])

  // Day 4 UI: Trash Bin Handlers
  const loadTrashFiles = async () => {
    try {
      const response = await axios.get('/api/v1/vault/trash', {
        params: { vault_type: currentVaultMode }
      })
      setTrashFiles(response.data.trash_files)
    } catch (error) {
      console.error('Failed to load trash:', error)
      toast.error('Failed to load trash')
    }
  }

  // Day 4 UI: Advanced Search Handler
  const handleAdvancedSearch = async () => {
    try {
      const params = new URLSearchParams({
        vault_type: currentVaultMode,
        ...(searchFilters.query && { query: searchFilters.query }),
        ...(searchFilters.mimeType && { mime_type: searchFilters.mimeType }),
        ...(searchFilters.tags.length > 0 && { tags: searchFilters.tags.join(',') }),
        ...(searchFilters.dateFrom && { date_from: searchFilters.dateFrom }),
        ...(searchFilters.dateTo && { date_to: searchFilters.dateTo }),
        ...(searchFilters.minSize && { min_size: searchFilters.minSize }),
        ...(searchFilters.maxSize && { max_size: searchFilters.maxSize }),
        ...(searchFilters.folderPath && { folder_path: searchFilters.folderPath })
      })

      const response = await axios.get(`/api/v1/vault/search?${params}`)
      setSearchResults(response.data.results)
      toast.success(`Found ${response.data.results.length} result(s)`)
    } catch (error) {
      console.error('Search failed:', error)
      toast.error('Search failed')
    }
  }

  // Day 4 UI: Share Handlers
  const handleCreateShareLink = async (fileId: string) => {
    try {
      const formData = new FormData()
      formData.append('vault_type', currentVaultMode)
      if (sharePassword) formData.append('password', sharePassword)
      if (shareExpiry) formData.append('expires_at', new Date(shareExpiry).toISOString())
      if (shareMaxDownloads) formData.append('max_downloads', shareMaxDownloads)
      formData.append('permissions', 'download')

      const response = await axios.post(
        `/api/v1/vault/files/${fileId}/share`,
        formData
      )

      const shareLink = `${window.location.origin}/vault/share/${response.data.share_token}`
      navigator.clipboard.writeText(shareLink)
      toast.success('Share link copied to clipboard!')

      loadFileShares(fileId)
      setSharePassword('')
      setShareExpiry('')
      setShareMaxDownloads('')
    } catch (error) {
      console.error('Share creation failed:', error)
      toast.error('Failed to create share link')
    }
  }

  // Day 4 UI: Version History Handlers
  const loadFileVersions = async (fileId: string) => {
    try {
      const response = await axios.get(`/api/v1/vault/files/${fileId}/versions`, {
        params: { vault_type: currentVaultMode }
      })
      setFileVersions(response.data.versions)
    } catch (error) {
      console.error('Failed to load versions:', error)
      toast.error('Failed to load file versions')
    }
  }

  const handleRestoreVersion = async (versionId: string) => {
    if (!confirm('Restore this version? The current version will be saved.')) return

    try {
      const formData = new FormData()
      formData.append('vault_type', currentVaultMode)

      await axios.post(`/api/v1/vault/versions/${versionId}/restore`, formData)
      toast.success('Version restored successfully')
      setShowVersionsModal(false)
      fetchFoldersAndFiles()
    } catch (error) {
      console.error('Restore version failed:', error)
      toast.error('Failed to restore version')
    }
  }

  // Day 4 UI: Comments Handlers
  const loadFileComments = async (fileId: string) => {
    try {
      const response = await axios.get(`/api/v1/vault/files/${fileId}/comments`, {
        params: { vault_type: currentVaultMode }
      })
      setFileComments(response.data.comments)
    } catch (error) {
      console.error('Failed to load comments:', error)
      toast.error('Failed to load comments')
    }
  }

  const handleAddComment = async () => {
    if (!newComment.trim() || !commentsFile) return

    try {
      const formData = new FormData()
      formData.append('vault_type', currentVaultMode)
      formData.append('comment_text', newComment.trim())

      await axios.post(`/api/v1/vault/files/${commentsFile.id}/comments`, formData)
      toast.success('Comment added')
      setNewComment('')
      loadFileComments(commentsFile.id)
    } catch (error) {
      console.error('Add comment failed:', error)
      toast.error('Failed to add comment')
    }
  }

  const handleDeleteComment = async (commentId: string) => {
    if (!confirm('Delete this comment?')) return

    try {
      await axios.delete(`/api/v1/vault/comments/${commentId}`, {
        params: { vault_type: currentVaultMode }
      })
      toast.success('Comment deleted')
      if (commentsFile) loadFileComments(commentsFile.id)
    } catch (error) {
      console.error('Delete comment failed:', error)
      toast.error('Failed to delete comment')
    }
  }

  // Day 4 UI: Pinned Files, Audit Logs, Export Handlers
  const [showPinnedModal, setShowPinnedModal] = useState(false)
  const [showAuditLogsModal, setShowAuditLogsModal] = useState(false)
  const [showExportModal, setShowExportModal] = useState(false)

  // Day 5: Analytics state
  const [showAnalyticsModal, setShowAnalyticsModal] = useState(false)
  const [analyticsData, setAnalyticsData] = useState<any>({
    storageTrends: null,
    accessPatterns: null,
    activityTimeline: null
  })

  // Day 5: WebSocket state
  const [wsConnected, setWsConnected] = useState(false)
  const [realtimeNotifications, setRealtimeNotifications] = useState<Array<{
    id: string
    type: string
    message: string
    timestamp: string
  }>>([])

  const loadPinnedFiles = async () => {
    try {
      const response = await axios.get('/api/v1/vault/pinned-files', {
        params: { vault_type: currentVaultMode }
      })
      setPinnedFiles(response.data.pinned_files)
    } catch (error) {
      console.error('Failed to load pinned files:', error)
    }
  }

  const handleTogglePin = async (fileId: string, isPinned: boolean) => {
    try {
      if (isPinned) {
        await axios.delete(`/api/v1/vault/files/${fileId}/pin`, {
          params: { vault_type: currentVaultMode }
        })
        toast.success('File unpinned')
      } else {
        const formData = new FormData()
        formData.append('vault_type', currentVaultMode)
        formData.append('pin_order', '0')
        await axios.post(`/api/v1/vault/files/${fileId}/pin`, formData)
        toast.success('File pinned')
      }
      loadPinnedFiles()
    } catch (error) {
      toast.error('Failed to toggle pin')
    }
  }

  const loadAuditLogs = async () => {
    try {
      const response = await axios.get('/api/v1/vault/audit-logs', {
        params: { vault_type: currentVaultMode, limit: 50 }
      })
      setAuditLogs(response.data.logs)
    } catch (error) {
      console.error('Failed to load audit logs:', error)
      toast.error('Failed to load audit logs')
    }
  }

  const handleExportVault = async () => {
    try {
      const response = await axios.get('/api/v1/vault/export', {
        params: { vault_type: currentVaultMode }
      })

      const dataStr = JSON.stringify(response.data, null, 2)
      const dataBlob = new Blob([dataStr], { type: 'application/json' })
      const url = URL.createObjectURL(dataBlob)
      const link = document.createElement('a')
      link.href = url
      link.download = `vault_export_${new Date().toISOString()}.json`
      link.click()
      URL.revokeObjectURL(url)

      toast.success('Vault data exported successfully')
    } catch (error) {
      console.error('Export failed:', error)
      toast.error('Failed to export vault data')
    }
  }

  // Day 5: Analytics Handlers
  const loadAnalytics = async () => {
    try {
      const [storageTrends, accessPatterns, activityTimeline] = await Promise.all([
        axios.get('/api/v1/vault/analytics/storage-trends', {
          params: { vault_type: currentVaultMode, days: 30 }
        }),
        axios.get('/api/v1/vault/analytics/access-patterns', {
          params: { vault_type: currentVaultMode, limit: 10 }
        }),
        axios.get('/api/v1/vault/analytics/activity-timeline', {
          params: { vault_type: currentVaultMode, hours: 24, limit: 50 }
        })
      ])

      setAnalyticsData({
        storageTrends: storageTrends.data,
        accessPatterns: accessPatterns.data,
        activityTimeline: activityTimeline.data
      })
    } catch (error) {
      console.error('Failed to load analytics:', error)
      toast.error('Failed to load analytics data')
    }
  }

  const loadFileShares = async (fileId: string) => {
    try {
      const response = await axios.get(`/api/v1/vault/files/${fileId}/shares`, {
        params: { vault_type: currentVaultMode }
      })
      setShareLinks(response.data.shares)
    } catch (error) {
      console.error('Failed to load shares:', error)
    }
  }

  const handleRevokeShare = async (shareId: string) => {
    try {
      await axios.delete(`/api/v1/vault/shares/${shareId}`, {
        params: { vault_type: currentVaultMode }
      })
      toast.success('Share link revoked')
      if (shareFile) loadFileShares(shareFile.id)
    } catch (error) {
      toast.error('Failed to revoke share')
    }
  }

  const handleRestoreFromTrash = async (fileId: string) => {
    try {
      const formData = new FormData()
      formData.append('vault_type', currentVaultMode)

      await axios.post(`/api/v1/vault/files/${fileId}/restore`, formData)
      toast.success('File restored from trash')
      loadTrashFiles()
      fetchFoldersAndFiles()
    } catch (error) {
      console.error('Restore failed:', error)
      toast.error('Failed to restore file')
    }
  }

  const handleEmptyTrash = async () => {
    if (!confirm('Permanently delete all files in trash? This cannot be undone!')) return

    try {
      await axios.delete('/api/v1/vault/trash/empty', {
        params: { vault_type: currentVaultMode }
      })
      toast.success('Trash emptied')
      setTrashFiles([])
    } catch (error) {
      console.error('Empty trash failed:', error)
      toast.error('Failed to empty trash')
    }
  }

  // Auto-lock after inactivity (5 minutes)
  useEffect(() => {
    if (!vaultUnlocked) return

    const resetTimer = () => {
      if (inactivityTimerRef.current) {
        clearTimeout(inactivityTimerRef.current)
      }

      inactivityTimerRef.current = setTimeout(() => {
        lockVault()
        toast.info('Vault locked due to inactivity')
      }, 5 * 60 * 1000) // 5 minutes
    }

    const events = ['mousedown', 'keydown', 'scroll', 'touchstart']
    events.forEach(event => document.addEventListener(event, resetTimer))

    resetTimer() // Start initial timer

    return () => {
      events.forEach(event => document.removeEventListener(event, resetTimer))
      if (inactivityTimerRef.current) {
        clearTimeout(inactivityTimerRef.current)
      }
    }
  }, [vaultUnlocked, lockVault])

  // Day 5: WebSocket connection for real-time updates
  useEffect(() => {
    if (!vaultUnlocked) {
      // Disconnect when vault is locked
      if (wsConnected) {
        vaultWebSocket.disconnect()
        setWsConnected(false)
      }
      return
    }

    // Connect to WebSocket when vault is unlocked
    vaultWebSocket.connect('default_user', currentVaultMode)

    // Handle connection events
    const handleConnected = () => {
      console.log('WebSocket connected to vault')
      setWsConnected(true)
      toast.success('Real-time sync enabled', { duration: 2000, icon: '🔗' })
    }

    const handleDisconnected = () => {
      console.log('WebSocket disconnected from vault')
      setWsConnected(false)
    }

    // Handle file events
    const handleFileEvent = (event: FileEvent) => {
      console.log('File event received:', event)

      // Add notification
      const notification = {
        id: crypto.randomUUID(),
        type: event.event,
        message: `${event.event.replace('file_', '')} ${event.file.filename || event.file.id}`,
        timestamp: event.timestamp
      }
      setRealtimeNotifications(prev => [notification, ...prev].slice(0, 5))

      // Show toast for file events
      if (event.event === 'file_uploaded') {
        toast.success(`File uploaded: ${event.file.filename}`, { icon: '📤' })
        // Refresh file list
        loadFiles()
      } else if (event.event === 'file_deleted') {
        toast.info(`File deleted`, { icon: '🗑️' })
        // Refresh file list
        loadFiles()
      } else if (event.event === 'file_renamed') {
        toast.info(`File renamed: ${event.file.new_filename}`, { icon: '✏️' })
        // Refresh file list
        loadFiles()
      } else if (event.event === 'file_moved') {
        toast.info(`File moved`, { icon: '📁' })
        // Refresh file list
        loadFiles()
      }
    }

    // Register event listeners
    vaultWebSocket.on('connected', handleConnected)
    vaultWebSocket.on('disconnected', handleDisconnected)
    vaultWebSocket.on('file_event', handleFileEvent)

    // Cleanup on unmount
    return () => {
      vaultWebSocket.off('connected', handleConnected)
      vaultWebSocket.off('disconnected', handleDisconnected)
      vaultWebSocket.off('file_event', handleFileEvent)
      vaultWebSocket.disconnect()
    }
  }, [vaultUnlocked, currentVaultMode])

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
      <div
        className="flex-1 p-6 overflow-auto"
        onDrop={handleFileDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <div className="max-w-6xl mx-auto">
          {/* Hidden File Input */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={(e) => {
              if (e.target.files) {
                handleFileUpload(e.target.files)
              }
            }}
            className="hidden"
          />

          {/* Upload Progress */}
          {uploadingFiles.length > 0 && (
            <div className="mb-6 space-y-2">
              {uploadingFiles.map((upload) => (
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
                      onClick={() => removeUploadedFile(upload.id)}
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
          {isDragging && (
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

          {/* Breadcrumb Navigation */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2 text-sm">
              {getBreadcrumbs().map((crumb, index) => (
                <div key={crumb.path} className="flex items-center gap-2">
                  {index > 0 && <ChevronRight className="w-4 h-4 text-gray-400" />}
                  <button
                    onClick={() => navigateToFolder(crumb.path)}
                    className={`flex items-center gap-1.5 px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors ${
                      crumb.path === currentFolderPath
                        ? 'text-blue-600 dark:text-blue-400 font-medium'
                        : 'text-gray-600 dark:text-gray-400'
                    }`}
                  >
                    {index === 0 ? (
                      <Home className="w-4 h-4" />
                    ) : (
                      <Folder className="w-4 h-4" />
                    )}
                    <span>{crumb.name}</span>
                  </button>
                </div>
              ))}
            </div>

            {/* New Folder Button */}
            <button
              onClick={() => setShowNewFolderModal(true)}
              className="px-3 py-1.5 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
            >
              <FolderPlus className="w-4 h-4" />
              New Folder
            </button>
          </div>

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
          <div className="flex items-center gap-3 mb-6 flex-wrap">
            {/* Upload Button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2 flex-shrink-0"
            >
              <Upload className="w-4 h-4" />
              Upload Files
            </button>

            {/* Multi-select Toggle */}
            <button
              onClick={toggleMultiSelectMode}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 flex-shrink-0 ${
                isMultiSelectMode
                  ? 'bg-purple-600 hover:bg-purple-700 text-white'
                  : 'bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100'
              }`}
            >
              <CheckSquare className="w-4 h-4" />
              {isMultiSelectMode ? 'Exit Select' : 'Select'}
            </button>

            {/* Storage Dashboard */}
            <button
              onClick={openStorageModal}
              className="px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 flex-shrink-0"
              title="View storage statistics"
            >
              <HardDrive className="w-4 h-4" />
              Storage
            </button>

            {/* Trash Bin Button */}
            <button
              onClick={() => {
                setShowTrashModal(true)
                loadTrashFiles()
              }}
              className="p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-700 dark:text-gray-300"
              title="Trash Bin"
            >
              <Trash2 className="w-4 h-4" />
            </button>

            {/* Advanced Search Button */}
            <button
              onClick={() => setShowAdvancedSearch(!showAdvancedSearch)}
              className={`p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded ${showAdvancedSearch ? 'bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300'}`}
              title="Advanced Search"
            >
              <SlidersHorizontal className="w-4 h-4" />
            </button>

            {/* Pinned Files Button */}
            <button
              onClick={() => {
                setShowPinnedModal(true)
                loadPinnedFiles()
              }}
              className="p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-700 dark:text-gray-300"
              title="Pinned Files"
            >
              <Pin className="w-4 h-4" />
            </button>

            {/* Audit Log Button */}
            <button
              onClick={() => {
                setShowAuditLogsModal(true)
                loadAuditLogs()
              }}
              className="p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-700 dark:text-gray-300"
              title="Audit Log"
            >
              <Activity className="w-4 h-4" />
            </button>

            {/* Export Button */}
            <button
              onClick={() => setShowExportModal(true)}
              className="p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-700 dark:text-gray-300"
              title="Export Vault"
            >
              <Archive className="w-4 h-4" />
            </button>

            {/* Analytics Button */}
            <button
              onClick={() => {
                setShowAnalyticsModal(true)
                loadAnalytics()
              }}
              className="p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-700 dark:text-gray-300"
              title="Analytics & Insights"
            >
              <BarChart3 className="w-4 h-4" />
            </button>

            {/* WebSocket Status Indicator */}
            <div className="relative">
              <button
                className={`p-2 rounded flex items-center gap-1 ${
                  wsConnected
                    ? 'text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20'
                    : 'text-gray-400 dark:text-gray-600 hover:bg-gray-200 dark:hover:bg-gray-700'
                }`}
                title={wsConnected ? 'Real-time sync active' : 'Real-time sync disconnected'}
              >
                {wsConnected ? (
                  <Wifi className="w-4 h-4" />
                ) : (
                  <WifiOff className="w-4 h-4" />
                )}
              </button>
              {realtimeNotifications.length > 0 && (
                <div className="absolute top-0 right-0 w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
              )}
            </div>

            {/* Bulk Actions (shown when in multi-select mode with selections) */}
            {isMultiSelectMode && selectedFiles.size > 0 && (
              <>
                <button
                  onClick={selectAll}
                  className="px-3 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
                >
                  <Check className="w-4 h-4" />
                  All
                </button>
                <button
                  onClick={deselectAll}
                  className="px-3 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
                >
                  <X className="w-4 h-4" />
                  None
                </button>
                <button
                  onClick={handleBulkDownload}
                  className="px-3 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
                >
                  <Download className="w-4 h-4" />
                  Download ({selectedFiles.size})
                </button>
                <button
                  onClick={handleBulkDelete}
                  className="px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete ({selectedFiles.size})
                </button>
              </>
            )}

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

            {/* Sort Files By */}
            <button
              onClick={() => handleSort(sortField)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center gap-2"
              title="Toggle sort direction"
            >
              <ArrowUpDown className="w-4 h-4" />
              {sortDirection === 'asc' ? '↑' : '↓'}
            </button>
            <select
              value={sortField}
              onChange={(e) => handleSort(e.target.value as any)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-amber-500 focus:border-transparent"
            >
              <option value="name">Name</option>
              <option value="date">Date</option>
              <option value="size">Size</option>
              <option value="type">Type</option>
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

          {/* Advanced Search Panel */}
          {showAdvancedSearch && (
            <div className="bg-gray-100 dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-lg p-4 mb-4">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-900 dark:text-gray-100">
                <Search className="w-5 h-5" />
                Advanced Search
              </h3>

              <div className="grid grid-cols-2 gap-4">
                {/* Text Query */}
                <div>
                  <label className="block text-sm mb-1 text-gray-700 dark:text-gray-300">Search Query</label>
                  <input
                    type="text"
                    value={searchFilters.query}
                    onChange={(e) => setSearchFilters({...searchFilters, query: e.target.value})}
                    className="w-full px-3 py-2 bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded text-gray-900 dark:text-gray-100"
                    placeholder="filename..."
                  />
                </div>

                {/* MIME Type */}
                <div>
                  <label className="block text-sm mb-1 text-gray-700 dark:text-gray-300">File Type</label>
                  <select
                    value={searchFilters.mimeType}
                    onChange={(e) => setSearchFilters({...searchFilters, mimeType: e.target.value})}
                    className="w-full px-3 py-2 bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded text-gray-900 dark:text-gray-100"
                  >
                    <option value="">All Types</option>
                    <option value="image">Images</option>
                    <option value="video">Videos</option>
                    <option value="audio">Audio</option>
                    <option value="text">Text</option>
                    <option value="application/pdf">PDF</option>
                  </select>
                </div>

                {/* Date Range */}
                <div>
                  <label className="block text-sm mb-1 text-gray-700 dark:text-gray-300">From Date</label>
                  <input
                    type="date"
                    value={searchFilters.dateFrom}
                    onChange={(e) => setSearchFilters({...searchFilters, dateFrom: e.target.value})}
                    className="w-full px-3 py-2 bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded text-gray-900 dark:text-gray-100"
                  />
                </div>

                <div>
                  <label className="block text-sm mb-1 text-gray-700 dark:text-gray-300">To Date</label>
                  <input
                    type="date"
                    value={searchFilters.dateTo}
                    onChange={(e) => setSearchFilters({...searchFilters, dateTo: e.target.value})}
                    className="w-full px-3 py-2 bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded text-gray-900 dark:text-gray-100"
                  />
                </div>

                {/* Size Range */}
                <div>
                  <label className="block text-sm mb-1 text-gray-700 dark:text-gray-300">Min Size (bytes)</label>
                  <input
                    type="number"
                    value={searchFilters.minSize}
                    onChange={(e) => setSearchFilters({...searchFilters, minSize: e.target.value})}
                    className="w-full px-3 py-2 bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded text-gray-900 dark:text-gray-100"
                  />
                </div>

                <div>
                  <label className="block text-sm mb-1 text-gray-700 dark:text-gray-300">Max Size (bytes)</label>
                  <input
                    type="number"
                    value={searchFilters.maxSize}
                    onChange={(e) => setSearchFilters({...searchFilters, maxSize: e.target.value})}
                    className="w-full px-3 py-2 bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded text-gray-900 dark:text-gray-100"
                  />
                </div>
              </div>

              <div className="flex gap-2 mt-4">
                <button
                  onClick={handleAdvancedSearch}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded"
                >
                  Search
                </button>
                <button
                  onClick={() => {
                    setSearchFilters({
                      query: '', mimeType: '', tags: [], dateFrom: '',
                      dateTo: '', minSize: '', maxSize: '', folderPath: ''
                    })
                    setSearchResults([])
                  }}
                  className="px-4 py-2 bg-gray-300 dark:bg-zinc-700 hover:bg-gray-400 dark:hover:bg-zinc-600 text-gray-900 dark:text-gray-100 rounded"
                >
                  Clear
                </button>
              </div>

              {/* Results */}
              {searchResults.length > 0 && (
                <div className="mt-4 pt-4 border-t border-gray-300 dark:border-zinc-700">
                  <h4 className="font-semibold mb-2 text-gray-900 dark:text-gray-100">Results ({searchResults.length})</h4>
                  <div className="grid grid-cols-2 gap-2">
                    {searchResults.map((file) => (
                      <div
                        key={file.id}
                        className="flex items-center gap-2 p-2 bg-white dark:bg-zinc-900 rounded hover:bg-gray-50 dark:hover:bg-zinc-800 cursor-pointer"
                        onClick={() => handlePreviewFile(file)}
                      >
                        <File className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                        <span className="flex-1 truncate text-sm text-gray-900 dark:text-gray-100">{file.filename}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Folders and Files Grid */}
          {(() => {
            // Apply search filter
            const filteredFolders = folders.filter(folder =>
              searchQuery === '' ||
              folder.folder_name.toLowerCase().includes(searchQuery.toLowerCase())
            )
            const searchFiltered = vaultFiles.filter(file =>
              searchQuery === '' ||
              file.filename.toLowerCase().includes(searchQuery.toLowerCase())
            )
            // Apply sorting
            const filteredFiles = sortFiles(searchFiltered)

            return (folders.length > 0 || vaultFiles.length > 0) ? (
              <div className="mb-8">
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">
                  Files & Folders ({filteredFolders.length + filteredFiles.length}
                  {searchQuery && ` of ${folders.length + vaultFiles.length}`})
                </h3>
                {filteredFolders.length === 0 && filteredFiles.length === 0 && searchQuery && (
                  <div className="text-center py-12">
                    <Search className="w-12 h-12 text-gray-400 dark:text-gray-600 mx-auto mb-3" />
                    <p className="text-gray-500 dark:text-gray-400">
                      No files or folders match "{searchQuery}"
                    </p>
                  </div>
                )}
                {(filteredFolders.length > 0 || filteredFiles.length > 0) && (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {/* Folders */}
                    {filteredFolders.map((folder) => {
                      const isDropTarget = dropTargetFolder === folder.folder_path

                      return (
                  <div
                    key={folder.id}
                    onClick={() => navigateToFolder(folder.folder_path)}
                    onContextMenu={(e) => handleFolderContextMenu(e, folder)}
                    onDragOver={(e) => handleFolderDragOver(e, folder.folder_path)}
                    onDragLeave={handleFolderDragLeave}
                    onDrop={(e) => handleFolderDrop(e, folder.folder_path)}
                    className={`group relative p-4 bg-white dark:bg-gray-800 border-2 rounded-lg hover:shadow-lg transition-all cursor-pointer ${
                      isDropTarget
                        ? 'border-green-500 dark:border-green-400 bg-green-50 dark:bg-green-900/20'
                        : 'border-gray-200 dark:border-gray-700 hover:border-blue-500 dark:hover:border-blue-400'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                        <Folder className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleFolderContextMenu(e as any, folder)
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-opacity"
                      >
                        <MoreVertical className="w-4 h-4 text-gray-500" />
                      </button>
                    </div>
                    <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-1 truncate">
                      {folder.folder_name}
                    </h3>
                    <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                      <Clock className="w-3 h-3" />
                      <span>{formatDate(folder.created_at)}</span>
                    </div>
                  </div>
                      )
                    })}

                {/* Uploaded Files */}
                {filteredFiles.map((file) => {
                  const FileIcon = getFileIcon(file.mime_type)
                  const iconColorClass = getFileIconColor(file.mime_type)
                  const isSelected = selectedFiles.has(file.id)
                  const isFavorite = favoriteFiles.has(file.id)

                  return (
                    <div
                      key={file.id}
                      draggable={!isMultiSelectMode}
                      onDragStart={(e) => handleFileDragStart(e, file)}
                      onDragEnd={handleFileDragEnd}
                      onClick={() => isMultiSelectMode ? toggleFileSelection(file.id) : handlePreviewFile(file)}
                      onContextMenu={(e) => handleFileContextMenu(e, file)}
                      className={`group relative p-4 bg-white dark:bg-gray-800 border-2 rounded-lg transition-all ${
                        isMultiSelectMode ? 'cursor-pointer' : 'cursor-move'
                      } ${
                        isSelected
                          ? 'border-purple-500 dark:border-purple-400 shadow-lg'
                          : 'border-gray-200 dark:border-gray-700 hover:border-purple-500 dark:hover:border-purple-400 hover:shadow-lg'
                      }`}
                    >
                      {/* Multi-select Checkbox */}
                      {isMultiSelectMode && (
                        <div className="absolute top-2 left-2 z-10">
                          <div className={`w-6 h-6 rounded flex items-center justify-center ${
                            isSelected ? 'bg-purple-600 text-white' : 'bg-gray-200 dark:bg-gray-700'
                          }`}>
                            {isSelected ? <Check className="w-4 h-4" /> : <Square className="w-4 h-4 text-gray-500" />}
                          </div>
                        </div>
                      )}

                      <div className="flex items-start justify-between mb-3">
                        {/* Day 5: Show thumbnail for images, icon for other files */}
                        {file.mime_type?.startsWith('image/') ? (
                          <div className="w-12 h-12 rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-700">
                            <img
                              src={`/api/v1/vault/files/${file.id}/thumbnail?vault_type=${currentVaultMode}&vault_passphrase=${encodeURIComponent(vaultPassphrase || '')}`}
                              alt={file.filename}
                              className="w-full h-full object-cover"
                              onError={(e) => {
                                // Fallback to icon if thumbnail fails
                                (e.target as HTMLElement).style.display = 'none'
                                const parent = (e.target as HTMLElement).parentElement
                                if (parent) {
                                  parent.innerHTML = `<div class="w-full h-full flex items-center justify-center ${iconColorClass}"><svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg></div>`
                                }
                              }}
                            />
                          </div>
                        ) : (
                          <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${iconColorClass}`}>
                            <FileIcon className="w-6 h-6" />
                          </div>
                        )}
                        <div className="opacity-0 group-hover:opacity-100 flex gap-1 transition-opacity">
                          {/* Favorite Button */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              toggleFavorite(file.id)
                            }}
                            className={`p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded ${
                              isFavorite ? 'text-yellow-500' : 'text-gray-500'
                            }`}
                            title={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
                          >
                            <Star className="w-4 h-4" fill={isFavorite ? 'currentColor' : 'none'} />
                          </button>
                          {/* Preview Button */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handlePreviewFile(file)
                            }}
                            className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                            title="Preview file"
                          >
                            <Eye className="w-4 h-4 text-gray-500" />
                          </button>
                          {/* Download Button */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleDownloadFile(file)
                            }}
                            className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                            title="Download file"
                          >
                            <Download className="w-4 h-4 text-gray-500" />
                          </button>
                          {/* Tag Button */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              openTagModal(file)
                            }}
                            className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                            title="Manage tags"
                          >
                            <Tag className="w-4 h-4 text-gray-500" />
                          </button>
                          {/* More Options */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleFileContextMenu(e as any, file)
                            }}
                            className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                            title="More options"
                          >
                            <MoreVertical className="w-4 h-4 text-gray-500" />
                          </button>
                        </div>
                      </div>
                      <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-1 truncate" title={file.filename}>
                        {file.filename}
                        {isFavorite && <Star className="inline w-3 h-3 ml-1 text-yellow-500" fill="currentColor" />}
                      </h3>
                      <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                        <div className="flex items-center gap-1">
                          <Shield className="w-3 h-3 text-green-600 dark:text-green-400" />
                          <span>Encrypted</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          <span>{formatDate(file.created_at)}</span>
                        </div>
                      </div>
                      <div className="mt-2 text-xs text-gray-400 dark:text-gray-500">
                        {formatBytes(file.file_size)}
                      </div>
                      {/* Tags Display */}
                      {fileTags.get(file.id) && fileTags.get(file.id)!.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {fileTags.get(file.id)!.map((tag) => (
                            <span
                              key={tag.tag_name}
                              className="px-2 py-0.5 text-xs rounded-full text-white"
                              style={{ backgroundColor: tag.tag_color }}
                            >
                              {tag.tag_name}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })}
                  </div>
                )}
              </div>
            ) : null
          })()}

          {/* Empty State */}
          {filteredDocs.length === 0 && vaultDocs.length === 0 && folders.length === 0 && vaultFiles.length === 0 && (
            <div className="text-center py-12">
              {/* Drag-Drop Upload Zone */}
              <button
                onClick={() => fileInputRef.current?.click()}
                className="w-full max-w-2xl mx-auto mb-8 p-12 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl hover:border-blue-500 dark:hover:border-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-all group cursor-pointer"
              >
                <Upload className="w-16 h-16 text-gray-400 group-hover:text-blue-600 dark:group-hover:text-blue-400 mx-auto mb-4" />
                <h4 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2 group-hover:text-blue-600 dark:group-hover:text-blue-400">
                  Upload Files to Vault
                </h4>
                <p className="text-gray-600 dark:text-gray-400">
                  Drag and drop files here, or click to browse
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">
                  All files will be encrypted automatically
                </p>
              </button>

              <div className="w-24 h-24 bg-amber-100 dark:bg-amber-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                <FolderOpen className="w-12 h-12 text-amber-600 dark:text-amber-400" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                Your Vault is Empty
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                Upload files or create encrypted documents
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

      {/* New Folder Modal */}
      {showNewFolderModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-md p-6 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-3 mb-4">
              <FolderPlus className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                Create New Folder
              </h3>
            </div>

            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Create a new folder in the current location.
            </p>

            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                Folder Name
              </label>
              <input
                type="text"
                value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleCreateFolder()}
                placeholder="e.g., Documents"
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                autoFocus
              />
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowNewFolderModal(false)
                  setNewFolderName('')
                }}
                className="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateFolder}
                disabled={!newFolderName.trim()}
                className="flex-1 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Create Folder
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Context Menu */}
      {contextMenu && (
        <div
          className="fixed z-50 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 py-1 min-w-[180px]"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onClick={() => setContextMenu(null)}
        >
          {contextMenu.type === 'file' && (
            <>
              <button
                onClick={() => handleDownloadFile(contextMenu.item)}
                className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3"
              >
                <Download className="w-4 h-4" />
                Download
              </button>
              <button
                onClick={() => startRename('file', contextMenu.item)}
                className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3"
              >
                <Edit2 className="w-4 h-4" />
                Rename
              </button>
              <button
                onClick={() => startMove(contextMenu.item)}
                className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3"
              >
                <FolderInput className="w-4 h-4" />
                Move to...
              </button>
              <button
                onClick={() => {
                  setShareFile(contextMenu.item)
                  setShowShareModal(true)
                  loadFileShares(contextMenu.item.id)
                  setContextMenu(null)
                }}
                className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3"
              >
                <Share2 className="w-4 h-4" />
                Share
              </button>
              <button
                onClick={() => {
                  setVersionsFile(contextMenu.item)
                  setShowVersionsModal(true)
                  loadFileVersions(contextMenu.item.id)
                  setContextMenu(null)
                }}
                className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3"
              >
                <History className="w-4 h-4" />
                Version History
              </button>
              <button
                onClick={() => {
                  setCommentsFile(contextMenu.item)
                  setShowCommentsModal(true)
                  loadFileComments(contextMenu.item.id)
                  setContextMenu(null)
                }}
                className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3"
              >
                <MessageSquare className="w-4 h-4" />
                Comments
              </button>
              <div className="border-t border-gray-200 dark:border-gray-700 my-1" />
              <button
                onClick={() => confirmDelete('file', contextMenu.item)}
                className="w-full px-4 py-2 text-left text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-3"
              >
                <Trash2 className="w-4 h-4" />
                Delete
              </button>
            </>
          )}
          {contextMenu.type === 'folder' && (
            <>
              <button
                onClick={() => startRename('folder', contextMenu.item)}
                className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3"
              >
                <Edit2 className="w-4 h-4" />
                Rename
              </button>
              <div className="border-t border-gray-200 dark:border-gray-700 my-1" />
              <button
                onClick={() => confirmDelete('folder', contextMenu.item)}
                className="w-full px-4 py-2 text-left text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-3"
              >
                <Trash2 className="w-4 h-4" />
                Delete
              </button>
            </>
          )}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-md p-6 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
                <Trash2 className="w-6 h-6 text-red-600 dark:text-red-400" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                Delete {deleteTarget.type === 'file' ? 'File' : 'Folder'}
              </h3>
            </div>

            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Are you sure you want to delete <strong>{deleteTarget.name}</strong>?
              {deleteTarget.type === 'folder' && ' This will also delete all files and subfolders inside it.'}
              {' '}This action cannot be undone.
            </p>

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowDeleteModal(false)
                  setDeleteTarget(null)
                }}
                className="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                className="flex-1 px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Rename Modal */}
      {showRenameModal && renameTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-md p-6 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-3 mb-4">
              <Edit2 className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                Rename {renameTarget.type === 'file' ? 'File' : 'Folder'}
              </h3>
            </div>

            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                New Name
              </label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleRename()}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                autoFocus
              />
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowRenameModal(false)
                  setRenameTarget(null)
                  setNewName('')
                }}
                className="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleRename}
                disabled={!newName.trim()}
                className="flex-1 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Rename
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Move File Modal */}
      {showMoveModal && moveTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-md p-6 border border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-3 mb-4">
              <FolderInput className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                Move File
              </h3>
            </div>

            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Select a folder to move <strong>{moveTarget.filename}</strong> to:
            </p>

            <div className="max-h-64 overflow-y-auto mb-4 border border-gray-200 dark:border-gray-700 rounded-lg">
              <button
                onClick={() => handleMove('/')}
                className="w-full px-4 py-2 text-left hover:bg-blue-50 dark:hover:bg-blue-900/20 flex items-center gap-2"
              >
                <Home className="w-4 h-4" />
                <span>Root</span>
              </button>
              {folders.map((folder) => (
                <button
                  key={folder.id}
                  onClick={() => handleMove(folder.folder_path)}
                  disabled={folder.folder_path === moveTarget.currentPath}
                  className="w-full px-4 py-2 text-left hover:bg-blue-50 dark:hover:bg-blue-900/20 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Folder className="w-4 h-4" />
                  <span>{folder.folder_path}</span>
                </button>
              ))}
            </div>

            <button
              onClick={() => {
                setShowMoveModal(false)
                setMoveTarget(null)
              }}
              className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Tag Management Modal */}
      {showTagModal && tagModalFile && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowTagModal(false)}>
          <div className="bg-white dark:bg-gray-900 rounded-lg max-w-md w-full" onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-3">
                <Tag className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                    Manage Tags
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {tagModalFile.filename}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowTagModal(false)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {/* Body */}
            <div className="p-4 space-y-4 max-h-[60vh] overflow-y-auto">
              {/* Add New Tag */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Add New Tag
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newTagName}
                    onChange={(e) => setNewTagName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') addTag()
                    }}
                    placeholder="Tag name"
                    className="flex-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                  />
                  <input
                    type="color"
                    value={newTagColor}
                    onChange={(e) => setNewTagColor(e.target.value)}
                    className="w-12 h-10 rounded-lg border border-gray-300 dark:border-gray-600 cursor-pointer"
                  />
                  <button
                    onClick={addTag}
                    disabled={!newTagName.trim()}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
                  >
                    Add
                  </button>
                </div>
              </div>

              {/* Existing Tags */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Current Tags
                </label>
                {fileTags.get(tagModalFile.id) && fileTags.get(tagModalFile.id)!.length > 0 ? (
                  <div className="space-y-2">
                    {fileTags.get(tagModalFile.id)!.map((tag) => (
                      <div
                        key={tag.tag_name}
                        className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded-lg"
                      >
                        <div className="flex items-center gap-2">
                          <div
                            className="w-4 h-4 rounded-full"
                            style={{ backgroundColor: tag.tag_color }}
                          />
                          <span className="text-sm text-gray-900 dark:text-gray-100">
                            {tag.tag_name}
                          </span>
                        </div>
                        <button
                          onClick={() => removeTag(tagModalFile.id, tag.tag_name)}
                          className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
                        >
                          <X className="w-4 h-4 text-gray-500" />
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                    No tags yet. Add one above.
                  </p>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="flex justify-end gap-2 p-4 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => setShowTagModal(false)}
                className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Storage Dashboard Modal */}
      {showStorageModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowStorageModal(false)}>
          <div className="bg-white dark:bg-gray-900 rounded-lg max-w-2xl w-full" onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-3">
                <HardDrive className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Storage Statistics
                </h3>
              </div>
              <button
                onClick={() => setShowStorageModal(false)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {/* Body */}
            <div className="p-6 space-y-6">
              {storageStats ? (
                <>
                  {/* Summary Stats */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
                      <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">Total Files</div>
                      <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                        {storageStats.total_files}
                      </div>
                    </div>
                    <div className="bg-purple-50 dark:bg-purple-900/20 p-4 rounded-lg">
                      <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">Total Size</div>
                      <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                        {formatBytes(storageStats.total_size)}
                      </div>
                    </div>
                  </div>

                  {/* Breakdown by Type */}
                  <div>
                    <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                      Storage by File Type
                    </h4>
                    <div className="space-y-3">
                      {storageStats.breakdown.map((item: any) => {
                        const percentage = storageStats.total_size > 0
                          ? (item.size / storageStats.total_size * 100).toFixed(1)
                          : 0

                        const colors: any = {
                          images: 'bg-blue-500',
                          videos: 'bg-purple-500',
                          audio: 'bg-green-500',
                          documents: 'bg-yellow-500',
                          other: 'bg-gray-500'
                        }

                        return (
                          <div key={item.category} className="space-y-1">
                            <div className="flex items-center justify-between text-sm">
                              <span className="text-gray-700 dark:text-gray-300 capitalize">
                                {item.category}
                              </span>
                              <span className="text-gray-600 dark:text-gray-400">
                                {item.count} files · {formatBytes(item.size)} · {percentage}%
                              </span>
                            </div>
                            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                              <div
                                className={`${colors[item.category] || 'bg-gray-500'} h-2 rounded-full transition-all`}
                                style={{ width: `${percentage}%` }}
                              />
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>

                  {/* Largest Files */}
                  {storageStats.largest_files && storageStats.largest_files.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                        Largest Files
                      </h4>
                      <div className="space-y-2">
                        {storageStats.largest_files.map((file: any) => (
                          <div
                            key={file.id}
                            className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                          >
                            <div className="flex items-center gap-3 flex-1 min-w-0">
                              <File className="w-4 h-4 text-gray-500 flex-shrink-0" />
                              <span className="text-sm text-gray-900 dark:text-gray-100 truncate">
                                {file.filename}
                              </span>
                            </div>
                            <span className="text-sm text-gray-600 dark:text-gray-400 ml-2">
                              {formatBytes(file.file_size)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  Loading storage statistics...
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex justify-end gap-2 p-4 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => setShowStorageModal(false)}
                className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Trash Bin Modal */}
      {showTrashModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setShowTrashModal(false)}>
          <div className="bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded-lg w-[800px] max-h-[80vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-300 dark:border-zinc-700">
              <div className="flex items-center gap-2">
                <Trash2 className="w-5 h-5 text-red-600 dark:text-red-400" />
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Trash Bin</h3>
              </div>
              <div className="flex items-center gap-2">
                {trashFiles.length > 0 && (
                  <button
                    onClick={handleEmptyTrash}
                    className="px-3 py-1 text-sm bg-red-600 hover:bg-red-700 text-white rounded"
                  >
                    Empty Trash
                  </button>
                )}
                <button onClick={() => setShowTrashModal(false)}>
                  <X className="w-5 h-5 text-gray-500" />
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4">
              {trashFiles.length === 0 ? (
                <div className="text-center py-12 text-gray-500 dark:text-zinc-500">
                  <Trash2 className="w-16 h-16 mx-auto mb-4 opacity-20" />
                  <p>Trash is empty</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {trashFiles.map((file) => (
                    <div
                      key={file.id}
                      className="flex items-center gap-4 p-3 bg-gray-100 dark:bg-zinc-800 rounded border border-gray-300 dark:border-zinc-700 hover:border-gray-400 dark:hover:border-zinc-600"
                    >
                      <File className="w-5 h-5 text-gray-500 dark:text-zinc-400" />
                      <div className="flex-1">
                        <div className="font-medium text-gray-900 dark:text-gray-100">{file.filename}</div>
                        <div className="text-sm text-gray-600 dark:text-zinc-500">
                          Deleted {new Date(file.deleted_at).toLocaleString()}
                        </div>
                      </div>
                      <button
                        onClick={() => handleRestoreFromTrash(file.id)}
                        className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm flex items-center gap-1"
                      >
                        <RotateCcw className="w-4 h-4" />
                        Restore
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Share Dialog Modal */}
      {showShareModal && shareFile && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setShowShareModal(false)}>
          <div className="bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded-lg w-[600px] overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b border-gray-300 dark:border-zinc-700">
              <h3 className="text-lg font-semibold flex items-center gap-2 text-gray-900 dark:text-gray-100">
                <Share2 className="w-5 h-5" />
                Share "{shareFile.filename}"
              </h3>
              <button onClick={() => setShowShareModal(false)}>
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            <div className="p-4 space-y-4">
              {/* Create New Share */}
              <div className="space-y-3">
                <h4 className="font-medium text-gray-900 dark:text-gray-100">Create Share Link</h4>

                <div>
                  <label className="block text-sm mb-1 text-gray-700 dark:text-gray-300">Password (optional)</label>
                  <input
                    type="password"
                    value={sharePassword}
                    onChange={(e) => setSharePassword(e.target.value)}
                    className="w-full px-3 py-2 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded text-gray-900 dark:text-gray-100"
                    placeholder="Leave empty for no password"
                  />
                </div>

                <div>
                  <label className="block text-sm mb-1 text-gray-700 dark:text-gray-300">Expires At (optional)</label>
                  <input
                    type="datetime-local"
                    value={shareExpiry}
                    onChange={(e) => setShareExpiry(e.target.value)}
                    className="w-full px-3 py-2 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded text-gray-900 dark:text-gray-100"
                  />
                </div>

                <div>
                  <label className="block text-sm mb-1 text-gray-700 dark:text-gray-300">Max Downloads (optional)</label>
                  <input
                    type="number"
                    value={shareMaxDownloads}
                    onChange={(e) => setShareMaxDownloads(e.target.value)}
                    className="w-full px-3 py-2 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded text-gray-900 dark:text-gray-100"
                    placeholder="Unlimited"
                  />
                </div>

                <button
                  onClick={() => handleCreateShareLink(shareFile.id)}
                  className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded flex items-center justify-center gap-2"
                >
                  <Link2 className="w-4 h-4" />
                  Create & Copy Link
                </button>
              </div>

              {/* Existing Shares */}
              {shareLinks.length > 0 && (
                <div className="pt-4 border-t border-gray-300 dark:border-zinc-700">
                  <h4 className="font-medium mb-2 text-gray-900 dark:text-gray-100">Active Share Links</h4>
                  <div className="space-y-2">
                    {shareLinks.map((share) => (
                      <div
                        key={share.id}
                        className="flex items-center gap-3 p-3 bg-gray-100 dark:bg-zinc-800 rounded"
                      >
                        <div className="flex-1 text-sm">
                          <div className="flex items-center gap-2">
                            <code className="text-xs text-gray-600 dark:text-zinc-400">
                              {share.share_token.substring(0, 20)}...
                            </code>
                            <button
                              onClick={() => {
                                navigator.clipboard.writeText(
                                  `${window.location.origin}/vault/share/${share.share_token}`
                                )
                                toast.success('Copied!')
                              }}
                              className="p-1 hover:bg-gray-200 dark:hover:bg-zinc-700 rounded"
                            >
                              <Copy className="w-3 h-3" />
                            </button>
                          </div>
                          <div className="text-gray-600 dark:text-zinc-500 mt-1">
                            Downloads: {share.download_count}/{share.max_downloads || '∞'}
                            {share.expires_at && ` • Expires: ${new Date(share.expires_at).toLocaleDateString()}`}
                          </div>
                        </div>
                        <button
                          onClick={() => handleRevokeShare(share.id)}
                          className="p-2 bg-red-600 hover:bg-red-700 text-white rounded"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Version History Modal */}
      {showVersionsModal && versionsFile && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setShowVersionsModal(false)}>
          <div className="bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded-lg w-[700px] max-h-[80vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b border-gray-300 dark:border-zinc-700">
              <h3 className="text-lg font-semibold flex items-center gap-2 text-gray-900 dark:text-gray-100">
                <GitBranch className="w-5 h-5" />
                Version History - "{versionsFile.filename}"
              </h3>
              <button onClick={() => setShowVersionsModal(false)}>
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {fileVersions.length === 0 ? (
                <div className="text-center py-12 text-gray-500 dark:text-zinc-500">
                  <GitBranch className="w-16 h-16 mx-auto mb-4 opacity-20" />
                  <p>No previous versions available</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {fileVersions.map((version, index) => (
                    <div
                      key={version.id}
                      className="flex items-center gap-4 p-4 bg-gray-100 dark:bg-zinc-800 rounded border border-gray-300 dark:border-zinc-700"
                    >
                      <div className="flex-shrink-0">
                        <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
                          <span className="text-sm font-bold text-blue-600 dark:text-blue-400">
                            v{version.version_number}
                          </span>
                        </div>
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-900 dark:text-gray-100">
                            Version {version.version_number}
                          </span>
                          {index === 0 && (
                            <span className="px-2 py-0.5 text-xs bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 rounded">
                              Current
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-gray-600 dark:text-zinc-500 mt-1">
                          Created {new Date(version.created_at).toLocaleString()}
                          {version.comment && ` • ${version.comment}`}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-zinc-600 mt-1">
                          Size: {(version.file_size / 1024).toFixed(2)} KB
                        </div>
                      </div>
                      {index !== 0 && (
                        <button
                          onClick={() => handleRestoreVersion(version.id)}
                          className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm flex items-center gap-1"
                        >
                          <RotateCcw className="w-4 h-4" />
                          Restore
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Comments Modal */}
      {showCommentsModal && commentsFile && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setShowCommentsModal(false)}>
          <div className="bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded-lg w-[600px] max-h-[80vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b border-gray-300 dark:border-zinc-700">
              <h3 className="text-lg font-semibold flex items-center gap-2 text-gray-900 dark:text-gray-100">
                <MessageSquare className="w-5 h-5" />
                Comments - "{commentsFile.filename}"
              </h3>
              <button onClick={() => setShowCommentsModal(false)}>
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {fileComments.length === 0 ? (
                <div className="text-center py-12 text-gray-500 dark:text-zinc-500">
                  <MessageSquare className="w-16 h-16 mx-auto mb-4 opacity-20" />
                  <p>No comments yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {fileComments.map((comment) => (
                    <div
                      key={comment.id}
                      className="p-3 bg-gray-100 dark:bg-zinc-800 rounded border border-gray-300 dark:border-zinc-700"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1">
                          <p className="text-gray-900 dark:text-gray-100">{comment.comment_text}</p>
                          <p className="text-xs text-gray-500 dark:text-zinc-600 mt-1">
                            {new Date(comment.created_at).toLocaleString()}
                            {comment.updated_at && ' (edited)'}
                          </p>
                        </div>
                        <button
                          onClick={() => handleDeleteComment(comment.id)}
                          className="p-1 hover:bg-red-100 dark:hover:bg-red-900/20 rounded text-red-600 dark:text-red-400"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Add Comment Input */}
            <div className="p-4 border-t border-gray-300 dark:border-zinc-700">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleAddComment()}
                  placeholder="Add a comment..."
                  className="flex-1 px-3 py-2 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded text-gray-900 dark:text-gray-100"
                />
                <button
                  onClick={handleAddComment}
                  disabled={!newComment.trim()}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded flex items-center gap-2"
                >
                  <Send className="w-4 h-4" />
                  Send
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Pinned Files Modal */}
      {showPinnedModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setShowPinnedModal(false)}>
          <div className="bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded-lg w-[700px] max-h-[80vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b border-gray-300 dark:border-zinc-700">
              <h3 className="text-lg font-semibold flex items-center gap-2 text-gray-900 dark:text-gray-100">
                <Pin className="w-5 h-5" />
                Pinned Files
              </h3>
              <button onClick={() => setShowPinnedModal(false)}>
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {pinnedFiles.length === 0 ? (
                <div className="text-center py-12 text-gray-500 dark:text-zinc-500">
                  <Pin className="w-16 h-16 mx-auto mb-4 opacity-20" />
                  <p>No pinned files</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {pinnedFiles.map((file) => (
                    <div
                      key={file.id}
                      className="flex items-center gap-4 p-3 bg-gray-100 dark:bg-zinc-800 rounded border border-gray-300 dark:border-zinc-700 hover:border-gray-400 dark:hover:border-zinc-600"
                    >
                      <File className="w-5 h-5 text-gray-500 dark:text-zinc-400" />
                      <div className="flex-1">
                        <div className="font-medium text-gray-900 dark:text-gray-100">{file.filename}</div>
                        <div className="text-sm text-gray-600 dark:text-zinc-500">
                          {(file.file_size / 1024).toFixed(2)} KB
                        </div>
                      </div>
                      <button
                        onClick={() => handleTogglePin(file.id, true)}
                        className="p-2 hover:bg-gray-200 dark:hover:bg-zinc-700 rounded text-gray-700 dark:text-gray-300"
                        title="Unpin"
                      >
                        <PinOff className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Audit Logs Modal */}
      {showAuditLogsModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setShowAuditLogsModal(false)}>
          <div className="bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded-lg w-[800px] max-h-[80vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b border-gray-300 dark:border-zinc-700">
              <h3 className="text-lg font-semibold flex items-center gap-2 text-gray-900 dark:text-gray-100">
                <Activity className="w-5 h-5" />
                Audit Log Timeline
              </h3>
              <button onClick={() => setShowAuditLogsModal(false)}>
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {auditLogs.length === 0 ? (
                <div className="text-center py-12 text-gray-500 dark:text-zinc-500">
                  <Activity className="w-16 h-16 mx-auto mb-4 opacity-20" />
                  <p>No activity logs</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {auditLogs.map((log) => (
                    <div
                      key={log.id}
                      className="flex items-start gap-3 p-3 bg-gray-100 dark:bg-zinc-800 rounded border border-gray-300 dark:border-zinc-700"
                    >
                      <div className="flex-shrink-0 mt-1">
                        <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-900 dark:text-gray-100">{log.action}</span>
                          <span className="text-xs px-2 py-0.5 bg-gray-200 dark:bg-zinc-700 rounded text-gray-700 dark:text-gray-300">
                            {log.resource_type}
                          </span>
                        </div>
                        {log.details && (
                          <p className="text-sm text-gray-600 dark:text-zinc-500 mt-1">{log.details}</p>
                        )}
                        <p className="text-xs text-gray-500 dark:text-zinc-600 mt-1">
                          {new Date(log.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Export Modal */}
      {showExportModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setShowExportModal(false)}>
          <div className="bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded-lg w-[500px] overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b border-gray-300 dark:border-zinc-700">
              <h3 className="text-lg font-semibold flex items-center gap-2 text-gray-900 dark:text-gray-100">
                <Archive className="w-5 h-5" />
                Export Vault Data
              </h3>
              <button onClick={() => setShowExportModal(false)}>
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            <div className="p-6">
              <p className="text-gray-700 dark:text-gray-300 mb-6">
                Export your vault metadata including file information, folders, tags, and more.
                Note: Actual file contents are not included in the export.
              </p>

              <div className="flex gap-3">
                <button
                  onClick={() => {
                    handleExportVault()
                    setShowExportModal(false)
                  }}
                  className="flex-1 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded flex items-center justify-center gap-2 font-medium"
                >
                  <Download className="w-5 h-5" />
                  Export as JSON
                </button>
                <button
                  onClick={() => setShowExportModal(false)}
                  className="px-4 py-3 bg-gray-200 dark:bg-zinc-700 hover:bg-gray-300 dark:hover:bg-zinc-600 text-gray-900 dark:text-gray-100 rounded"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Analytics Modal */}
      {showAnalyticsModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={() => setShowAnalyticsModal(false)}>
          <div className="bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded-lg w-[900px] max-h-[90vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b border-gray-300 dark:border-zinc-700">
              <h3 className="text-lg font-semibold flex items-center gap-2 text-gray-900 dark:text-gray-100">
                <BarChart3 className="w-5 h-5" />
                Vault Analytics & Insights
              </h3>
              <button onClick={() => setShowAnalyticsModal(false)}>
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              {/* Storage Trends */}
              {analyticsData.storageTrends && (
                <div className="mb-6">
                  <h4 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-900 dark:text-gray-100">
                    <TrendingUp className="w-5 h-5" />
                    Storage Trends (Last 30 Days)
                  </h4>
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                      <div className="text-sm text-blue-700 dark:text-blue-300 mb-1">Total Files</div>
                      <div className="text-2xl font-bold text-blue-900 dark:text-blue-100">
                        {analyticsData.storageTrends.total_files}
                      </div>
                    </div>
                    <div className="p-4 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg">
                      <div className="text-sm text-purple-700 dark:text-purple-300 mb-1">Total Storage</div>
                      <div className="text-2xl font-bold text-purple-900 dark:text-purple-100">
                        {(analyticsData.storageTrends.total_bytes / (1024 * 1024)).toFixed(2)} MB
                      </div>
                    </div>
                  </div>
                  {analyticsData.storageTrends.trends.length > 0 ? (
                    <div className="space-y-2">
                      {analyticsData.storageTrends.trends.slice(0, 5).map((trend: any) => (
                        <div key={trend.date} className="flex items-center justify-between p-3 bg-gray-100 dark:bg-zinc-800 rounded border border-gray-300 dark:border-zinc-700">
                          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{trend.date}</span>
                          <div className="flex gap-4 text-sm">
                            <span className="text-blue-600 dark:text-blue-400">{trend.files_added} files</span>
                            <span className="text-purple-600 dark:text-purple-400">
                              +{(trend.bytes_added / (1024 * 1024)).toFixed(2)} MB
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-center text-gray-500 dark:text-zinc-500 py-4">No storage activity in the last 30 days</p>
                  )}
                </div>
              )}

              {/* Access Patterns */}
              {analyticsData.accessPatterns && (
                <div className="mb-6">
                  <h4 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-900 dark:text-gray-100">
                    <Activity className="w-5 h-5" />
                    Access Patterns
                  </h4>
                  <div className="grid grid-cols-3 gap-4 mb-4">
                    <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg text-center">
                      <div className="text-sm text-green-700 dark:text-green-300 mb-1">Views</div>
                      <div className="text-xl font-bold text-green-900 dark:text-green-100">
                        {analyticsData.accessPatterns.access_by_type?.view || 0}
                      </div>
                    </div>
                    <div className="p-4 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg text-center">
                      <div className="text-sm text-orange-700 dark:text-orange-300 mb-1">Downloads</div>
                      <div className="text-xl font-bold text-orange-900 dark:text-orange-100">
                        {analyticsData.accessPatterns.access_by_type?.download || 0}
                      </div>
                    </div>
                    <div className="p-4 bg-teal-50 dark:bg-teal-900/20 border border-teal-200 dark:border-teal-800 rounded-lg text-center">
                      <div className="text-sm text-teal-700 dark:text-teal-300 mb-1">Last 24h</div>
                      <div className="text-xl font-bold text-teal-900 dark:text-teal-100">
                        {analyticsData.accessPatterns.recent_access_24h}
                      </div>
                    </div>
                  </div>
                  <h5 className="text-md font-semibold mb-2 text-gray-900 dark:text-gray-100">Most Accessed Files</h5>
                  {analyticsData.accessPatterns.most_accessed.length > 0 ? (
                    <div className="space-y-2">
                      {analyticsData.accessPatterns.most_accessed.slice(0, 5).map((file: any) => (
                        <div key={file.id} className="flex items-center justify-between p-3 bg-gray-100 dark:bg-zinc-800 rounded border border-gray-300 dark:border-zinc-700">
                          <div className="flex-1 truncate">
                            <div className="font-medium text-gray-900 dark:text-gray-100 truncate">{file.filename}</div>
                            <div className="text-xs text-gray-600 dark:text-gray-400">
                              {(file.file_size / 1024).toFixed(2)} KB • {file.mime_type}
                            </div>
                          </div>
                          <span className="text-sm font-semibold text-blue-600 dark:text-blue-400 ml-4">
                            {file.access_count} accesses
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-center text-gray-500 dark:text-zinc-500 py-4">No file access recorded yet</p>
                  )}
                </div>
              )}

              {/* Activity Timeline */}
              {analyticsData.activityTimeline && (
                <div>
                  <h4 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-900 dark:text-gray-100">
                    <Clock className="w-5 h-5" />
                    Recent Activity (Last 24 Hours)
                  </h4>
                  {Object.keys(analyticsData.activityTimeline.action_summary).length > 0 && (
                    <div className="grid grid-cols-4 gap-2 mb-4">
                      {Object.entries(analyticsData.activityTimeline.action_summary).map(([action, count]: [string, any]) => (
                        <div key={action} className="p-3 bg-gray-100 dark:bg-zinc-800 rounded border border-gray-300 dark:border-zinc-700 text-center">
                          <div className="text-xs text-gray-600 dark:text-gray-400 mb-1 truncate">{action}</div>
                          <div className="text-lg font-bold text-gray-900 dark:text-gray-100">{count}</div>
                        </div>
                      ))}
                    </div>
                  )}
                  {analyticsData.activityTimeline.activities.length > 0 ? (
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {analyticsData.activityTimeline.activities.slice(0, 10).map((activity: any, index: number) => (
                        <div key={index} className="flex items-start gap-3 p-3 bg-gray-100 dark:bg-zinc-800 rounded border border-gray-300 dark:border-zinc-700">
                          <div className="flex-shrink-0 mt-1">
                            <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-gray-900 dark:text-gray-100">{activity.action}</span>
                              <span className="text-xs px-2 py-0.5 bg-gray-200 dark:bg-zinc-700 rounded text-gray-700 dark:text-gray-300 truncate">
                                {activity.resource_type}
                              </span>
                            </div>
                            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                              {new Date(activity.timestamp).toLocaleString()}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-center text-gray-500 dark:text-zinc-500 py-4">No recent activity</p>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* File Preview Modal */}
      {showPreviewModal && previewFile && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => {
          setShowPreviewModal(false)
          if (previewContent) URL.revokeObjectURL(previewContent)
        }}>
          <div className="bg-white dark:bg-gray-900 rounded-lg max-w-6xl w-full max-h-[90vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-3">
                <Eye className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                <div>
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                    {previewFile.filename}
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {previewFile.mime_type} • {formatBytes(previewFile.file_size)}
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  setShowPreviewModal(false)
                  if (previewContent) URL.revokeObjectURL(previewContent)
                }}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {/* Preview Content */}
            <div className="flex-1 overflow-auto p-4 bg-gray-50 dark:bg-gray-800">
              {previewContent && (
                <>
                  {/* Image Preview */}
                  {previewFile.mime_type.startsWith('image/') && (
                    <div className="flex flex-col items-center gap-4">
                      <div className="flex gap-2">
                        <button
                          onClick={() => setPreviewZoom(Math.max(0.25, previewZoom - 0.25))}
                          className="px-3 py-2 bg-white dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg flex items-center gap-2"
                        >
                          <ZoomOut className="w-4 h-4" />
                          Zoom Out
                        </button>
                        <button
                          onClick={() => setPreviewZoom(1)}
                          className="px-3 py-2 bg-white dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg"
                        >
                          Reset
                        </button>
                        <button
                          onClick={() => setPreviewZoom(previewZoom + 0.25)}
                          className="px-3 py-2 bg-white dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg flex items-center gap-2"
                        >
                          <ZoomIn className="w-4 h-4" />
                          Zoom In
                        </button>
                      </div>
                      <img
                        src={previewContent}
                        alt={previewFile.filename}
                        style={{ transform: `scale(${previewZoom})`, transition: 'transform 0.2s' }}
                        className="max-w-full"
                      />
                    </div>
                  )}

                  {/* PDF Preview */}
                  {previewFile.mime_type === 'application/pdf' && (
                    <iframe
                      src={previewContent}
                      className="w-full h-[600px] rounded-lg"
                      title={previewFile.filename}
                    />
                  )}

                  {/* Text/Code Preview */}
                  {(previewFile.mime_type.startsWith('text/') || previewFile.mime_type === 'application/json') && (
                    <pre className="bg-white dark:bg-gray-900 p-4 rounded-lg overflow-auto text-sm font-mono">
                      <code>{previewContent}</code>
                    </pre>
                  )}

                  {/* Audio Preview */}
                  {previewFile.mime_type.startsWith('audio/') && (
                    <div className="flex items-center justify-center h-full">
                      <audio controls className="w-full max-w-2xl">
                        <source src={previewContent} type={previewFile.mime_type} />
                        Your browser does not support the audio element.
                      </audio>
                    </div>
                  )}

                  {/* Video Preview */}
                  {previewFile.mime_type.startsWith('video/') && (
                    <div className="flex items-center justify-center">
                      <video controls className="w-full max-w-4xl rounded-lg">
                        <source src={previewContent} type={previewFile.mime_type} />
                        Your browser does not support the video element.
                      </video>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Footer with Actions */}
            <div className="flex items-center justify-end gap-2 p-4 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => handleDownloadFile(previewFile)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-2"
              >
                <Download className="w-4 h-4" />
                Download
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
