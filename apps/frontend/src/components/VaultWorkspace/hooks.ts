/**
 * VaultWorkspace Custom Hooks
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { useDocsStore } from '@/stores/docsStore'
import { useUserStore } from '@/stores/userStore'
import { vaultWebSocket } from '@/lib/websocketClient'
import type { FileEvent } from '@/lib/websocketClient'
import axios from 'axios'
import toast from 'react-hot-toast'
import { isBiometricAvailable, authenticateBiometric } from '@/lib/biometricAuth'
import type {
  VaultFile,
  VaultFolder,
  FileTag,
  UploadProgress,
  SearchFilters,
  ShareLinkData,
  FileVersion,
  FileComment,
  StorageStats,
  AuditLogEntry,
  RealtimeNotification,
  AnalyticsData,
  TrashFile
} from './types'

/**
 * Hook for vault authentication state and handlers
 */
export function useVaultAuth() {
  const {
    vaultUnlocked,
    unlockVault,
    lockVault,
    currentVaultMode,
    securitySettings,
    vaultPassphrase
  } = useDocsStore()

  const requireTouchID = securitySettings.require_touch_id
  const [isAuthenticating, setIsAuthenticating] = useState(false)
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [biometricAvailable, setBiometricAvailable] = useState(false)
  const [authError, setAuthError] = useState('')

  useEffect(() => {
    const checkBiometric = async () => {
      const available = await isBiometricAvailable()
      setBiometricAvailable(available)
    }
    checkBiometric()
  }, [])

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

  return {
    vaultUnlocked,
    lockVault,
    currentVaultMode,
    vaultPassphrase,
    requireTouchID,
    isAuthenticating,
    password,
    setPassword,
    showPassword,
    setShowPassword,
    biometricAvailable,
    authError,
    handleUnlock,
    handleKeyPress,
    securitySettings
  }
}

/**
 * Hook for vault workspace state (files, folders, navigation)
 */
export function useVaultWorkspace() {
  const { currentVaultMode } = useDocsStore()
  const [currentFolderPath, setCurrentFolderPath] = useState('/')
  const [folders, setFolders] = useState<VaultFolder[]>([])
  const [vaultFiles, setVaultFiles] = useState<VaultFile[]>([])

  const fetchFoldersAndFiles = useCallback(async () => {
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
    } catch (error) {
      console.error('Failed to fetch vault contents:', error)
    }
  }, [currentVaultMode, currentFolderPath])

  const navigateToFolder = (folderPath: string) => {
    setCurrentFolderPath(folderPath)
  }

  const navigateUp = () => {
    if (currentFolderPath === '/') return
    const parts = currentFolderPath.split('/').filter(Boolean)
    parts.pop()
    const parentPath = parts.length > 0 ? '/' + parts.join('/') : '/'
    setCurrentFolderPath(parentPath)
  }

  return {
    currentFolderPath,
    folders,
    vaultFiles,
    setVaultFiles,
    setFolders,
    fetchFoldersAndFiles,
    navigateToFolder,
    navigateUp
  }
}

/**
 * Hook for file operations (upload, download, delete, rename, move)
 */
export function useFileOperations(currentVaultMode: string, vaultPassphrase: string | null, currentFolderPath: string) {
  const [uploadingFiles, setUploadingFiles] = useState<UploadProgress[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

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

  const handleFileUpload = async (files: FileList | File[], onComplete?: () => void) => {
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

    // Call completion callback
    if (onComplete) {
      onComplete()
    }
  }

  const handleDownloadFile = async (file: VaultFile) => {
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

  const removeUploadedFile = (uploadId: string) => {
    setUploadingFiles(prev => prev.filter(u => u.id !== uploadId))
  }

  return {
    uploadingFiles,
    fileInputRef,
    handleFileUpload,
    handleDownloadFile,
    removeUploadedFile,
    setUploadingFiles
  }
}

/**
 * Hook for multi-select functionality
 */
export function useSelection() {
  const [isMultiSelectMode, setIsMultiSelectMode] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set())
  const [selectedFolders, setSelectedFolders] = useState<Set<string>>(new Set())

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

  const selectAll = (fileIds: string[], folderIds: string[]) => {
    setSelectedFiles(new Set(fileIds))
    setSelectedFolders(new Set(folderIds))
  }

  const deselectAll = () => {
    setSelectedFiles(new Set())
    setSelectedFolders(new Set())
  }

  return {
    isMultiSelectMode,
    selectedFiles,
    selectedFolders,
    toggleMultiSelectMode,
    toggleFileSelection,
    selectAll,
    deselectAll,
    setIsMultiSelectMode
  }
}

/**
 * Hook for drag-and-drop functionality
 */
export function useDragDrop() {
  const [isDragging, setIsDragging] = useState(false)
  const [draggedFile, setDraggedFile] = useState<VaultFile | null>(null)
  const [dropTargetFolder, setDropTargetFolder] = useState<string | null>(null)

  const handleFileDragStart = (e: React.DragEvent, file: VaultFile) => {
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

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  return {
    isDragging,
    setIsDragging,
    draggedFile,
    setDraggedFile,
    dropTargetFolder,
    setDropTargetFolder,
    handleFileDragStart,
    handleFileDragEnd,
    handleFolderDragOver,
    handleFolderDragLeave,
    handleDragOver,
    handleDragLeave
  }
}

/**
 * Hook for WebSocket real-time updates
 */
export function useWebSocket(vaultUnlocked: boolean, currentVaultMode: string, onFileUpdate: () => void) {
  const { getUserId } = useUserStore()
  const userId = getUserId()
  const [wsConnected, setWsConnected] = useState(false)
  const [realtimeNotifications, setRealtimeNotifications] = useState<RealtimeNotification[]>([])

  useEffect(() => {
    if (!vaultUnlocked) {
      if (wsConnected) {
        vaultWebSocket.disconnect()
        setWsConnected(false)
      }
      return
    }

    // Connect to WebSocket when vault is unlocked
    vaultWebSocket.connect(userId, currentVaultMode)

    const handleConnected = () => {
      console.log('WebSocket connected to vault')
      setWsConnected(true)
      toast.success('Real-time sync enabled', { duration: 2000, icon: '🔗' })
    }

    const handleDisconnected = () => {
      console.log('WebSocket disconnected from vault')
      setWsConnected(false)
    }

    const handleFileEvent = (event: FileEvent) => {
      console.log('File event received:', event)

      const notification = {
        id: crypto.randomUUID(),
        type: event.event,
        message: `${event.event.replace('file_', '')} ${event.file.filename || event.file.id}`,
        timestamp: event.timestamp
      }
      setRealtimeNotifications(prev => [notification, ...prev].slice(0, 5))

      if (event.event === 'file_uploaded') {
        toast.success(`File uploaded: ${event.file.filename}`, { icon: '📤' })
        onFileUpdate()
      } else if (event.event === 'file_deleted') {
        toast.info(`File deleted`, { icon: '🗑️' })
        onFileUpdate()
      } else if (event.event === 'file_renamed') {
        toast.info(`File renamed: ${event.file.new_filename}`, { icon: '✏️' })
        onFileUpdate()
      } else if (event.event === 'file_moved') {
        toast.info(`File moved`, { icon: '📁' })
        onFileUpdate()
      }
    }

    vaultWebSocket.on('connected', handleConnected)
    vaultWebSocket.on('disconnected', handleDisconnected)
    vaultWebSocket.on('file_event', handleFileEvent)

    return () => {
      vaultWebSocket.off('connected', handleConnected)
      vaultWebSocket.off('disconnected', handleDisconnected)
      vaultWebSocket.off('file_event', handleFileEvent)
      vaultWebSocket.disconnect()
    }
  }, [vaultUnlocked, currentVaultMode, userId, onFileUpdate, wsConnected])

  return { wsConnected, realtimeNotifications }
}

/**
 * Hook for auto-lock functionality
 */
export function useAutoLock(vaultUnlocked: boolean, lockVault: () => void) {
  const inactivityTimerRef = useRef<NodeJS.Timeout | null>(null)

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

    resetTimer()

    return () => {
      events.forEach(event => document.removeEventListener(event, resetTimer))
      if (inactivityTimerRef.current) {
        clearTimeout(inactivityTimerRef.current)
      }
    }
  }, [vaultUnlocked, lockVault])
}
