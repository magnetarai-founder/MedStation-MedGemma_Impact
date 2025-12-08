/**
 * Recipient File Share Component
 *
 * Proton Drive-style end-to-end encrypted file sharing
 * Files are encrypted client-side and only accessible to specified recipients
 */

import { useState, useRef } from 'react'
import { Lock, Upload, X, Share2, Check, Loader2, Download, Trash2, Users } from 'lucide-react'
import toast from 'react-hot-toast'
import {
  createFileShare,
  decryptSharedFile,
  type EncryptedFileShare,
} from '@/lib/publicKeyEncryption'

interface Recipient {
  id: string
  name: string
  email?: string
  publicKey: string
}

interface RecipientFileShareProps {
  currentUserId: string
  currentUserName: string
  availableRecipients: Recipient[]
  onFileShared?: (share: EncryptedFileShare) => void
}

export function RecipientFileShare({
  currentUserId,
  currentUserName,
  availableRecipients,
  onFileShared,
}: RecipientFileShareProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [selectedRecipients, setSelectedRecipients] = useState<Set<string>>(new Set())
  const [isSharing, setIsSharing] = useState(false)
  const [showRecipientPicker, setShowRecipientPicker] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedFile(file)
    }
  }

  function toggleRecipient(recipientId: string) {
    const newSelected = new Set(selectedRecipients)
    if (newSelected.has(recipientId)) {
      newSelected.delete(recipientId)
    } else {
      newSelected.add(recipientId)
    }
    setSelectedRecipients(newSelected)
  }

  function selectAllRecipients() {
    setSelectedRecipients(new Set(availableRecipients.map((r) => r.id)))
  }

  function clearAllRecipients() {
    setSelectedRecipients(new Set())
  }

  async function handleShareFile() {
    if (!selectedFile) {
      toast.error('Please select a file to share')
      return
    }

    if (selectedRecipients.size === 0) {
      toast.error('Please select at least one recipient')
      return
    }

    setIsSharing(true)

    try {
      // Get selected recipient details
      const recipients = availableRecipients.filter((r) => selectedRecipients.has(r.id))

      // Create encrypted file share
      const fileShare = await createFileShare(selectedFile, recipients, currentUserName)

      // TODO: Upload to backend
      // await api.uploadEncryptedFileShare(fileShare)

      // Mock: simulate upload delay
      await new Promise((resolve) => setTimeout(resolve, 1000))

      toast.success(`File shared with ${recipients.length} recipient(s)`)
      onFileShared?.(fileShare)

      // Reset form
      setSelectedFile(null)
      setSelectedRecipients(new Set())
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    } catch (err) {
      toast.error(`Failed to share file: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setIsSharing(false)
    }
  }

  const selectedRecipientsList = availableRecipients.filter((r) => selectedRecipients.has(r.id))

  return (
    <div className="space-y-4">
      {/* File Upload */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Select File
        </label>
        <div className="relative">
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileSelect}
            className="hidden"
            id="recipient-file-input"
          />
          <label
            htmlFor="recipient-file-input"
            className="flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg cursor-pointer hover:border-blue-500 dark:hover:border-blue-400 transition-colors"
          >
            <Upload className="w-5 h-5 text-gray-400" />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {selectedFile ? selectedFile.name : 'Choose file to share'}
            </span>
          </label>

          {selectedFile && (
            <button
              onClick={() => {
                setSelectedFile(null)
                if (fileInputRef.current) {
                  fileInputRef.current.value = ''
                }
              }}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            >
              <X className="w-4 h-4 text-gray-400" />
            </button>
          )}
        </div>

        {selectedFile && (
          <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            Size: {(selectedFile.size / 1024).toFixed(2)} KB
          </div>
        )}
      </div>

      {/* Recipient Selection */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Share with Recipients
          </label>
          <div className="flex items-center gap-2">
            <button
              onClick={selectAllRecipients}
              className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
            >
              Select All
            </button>
            {selectedRecipients.size > 0 && (
              <button
                onClick={clearAllRecipients}
                className="text-xs text-gray-600 dark:text-gray-400 hover:underline"
              >
                Clear
              </button>
            )}
          </div>
        </div>

        <div className="border border-gray-300 dark:border-gray-600 rounded-lg p-3 max-h-64 overflow-y-auto">
          {availableRecipients.length === 0 ? (
            <div className="text-center py-4 text-gray-500 dark:text-gray-400 text-sm">
              <Users className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No recipients available</p>
            </div>
          ) : (
            <div className="space-y-2">
              {availableRecipients.map((recipient) => {
                const isSelected = selectedRecipients.has(recipient.id)

                return (
                  <div
                    key={recipient.id}
                    onClick={() => toggleRecipient(recipient.id)}
                    className={`flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800'
                        : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 ${
                        isSelected
                          ? 'bg-blue-600 border-blue-600'
                          : 'border-gray-300 dark:border-gray-600'
                      }`}
                    >
                      {isSelected && <Check className="w-3 h-3 text-white" />}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {recipient.name}
                      </div>
                      {recipient.email && (
                        <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                          {recipient.email}
                        </div>
                      )}
                    </div>

                    <Lock className="w-4 h-4 text-gray-400 flex-shrink-0" />
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {selectedRecipients.size > 0 && (
          <div className="mt-2 text-xs text-gray-600 dark:text-gray-400">
            {selectedRecipients.size} recipient{selectedRecipients.size !== 1 ? 's' : ''} selected
          </div>
        )}
      </div>

      {/* Share Button */}
      <button
        onClick={handleShareFile}
        disabled={!selectedFile || selectedRecipients.size === 0 || isSharing}
        className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isSharing ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>Encrypting & Sharing...</span>
          </>
        ) : (
          <>
            <Share2 className="w-5 h-5" />
            <span>Share File (End-to-End Encrypted)</span>
          </>
        )}
      </button>

      {/* Info Banner */}
      <div className="flex items-start gap-2 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
        <Lock className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
        <div className="text-xs text-blue-900 dark:text-blue-100">
          <p className="font-medium mb-1">End-to-End Encrypted Sharing</p>
          <p className="text-blue-700 dark:text-blue-300">
            Files are encrypted on your device before upload. Only selected recipients with their
            private keys can decrypt and view the file. Not even the server can access the content.
          </p>
        </div>
      </div>
    </div>
  )
}

/**
 * Shared Files List Component
 *
 * Shows files shared with the current user
 */

interface SharedFilesListProps {
  sharedFiles: EncryptedFileShare[]
  currentUserId: string
  currentUserPrivateKey: CryptoKey
  onFileDeleted?: (fileId: string) => void
}

export function SharedFilesList({
  sharedFiles,
  currentUserId,
  currentUserPrivateKey,
  onFileDeleted,
}: SharedFilesListProps) {
  const [downloadingFiles, setDownloadingFiles] = useState<Set<string>>(new Set())

  async function handleDownloadFile(fileShare: EncryptedFileShare) {
    setDownloadingFiles((prev) => new Set(prev).add(fileShare.fileId))

    try {
      // Decrypt the file
      const decryptedBlob = await decryptSharedFile(
        fileShare,
        currentUserId,
        currentUserPrivateKey
      )

      // Download the file
      const url = URL.createObjectURL(decryptedBlob)
      const a = document.createElement('a')
      a.href = url
      a.download = fileShare.filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)

      toast.success('File downloaded successfully')
    } catch (err) {
      toast.error(`Failed to download file: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setDownloadingFiles((prev) => {
        const newSet = new Set(prev)
        newSet.delete(fileShare.fileId)
        return newSet
      })
    }
  }

  function handleDeleteFile(fileId: string) {
    if (confirm('Are you sure you want to delete this shared file?')) {
      // TODO: Call backend API
      // await api.deleteSharedFile(fileId)
      onFileDeleted?.(fileId)
      toast.success('File deleted')
    }
  }

  if (sharedFiles.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <Share2 className="w-12 h-12 mx-auto mb-3 opacity-50" />
        <p className="text-sm">No shared files yet</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {sharedFiles.map((fileShare) => {
        const isDownloading = downloadingFiles.has(fileShare.fileId)
        const hasAccess = fileShare.recipients.some((r) => r.recipientId === currentUserId)

        return (
          <div
            key={fileShare.fileId}
            className="flex items-center gap-3 p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg"
          >
            <div className="p-2 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
              <Lock className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>

            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                {fileShare.filename}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Shared by {fileShare.uploadedBy} • {(fileShare.fileSize / 1024).toFixed(2)} KB •{' '}
                {fileShare.recipients.length} recipient{fileShare.recipients.length !== 1 ? 's' : ''}
              </div>
            </div>

            <div className="flex items-center gap-2">
              {hasAccess && (
                <button
                  onClick={() => handleDownloadFile(fileShare)}
                  disabled={isDownloading}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
                  title="Download & decrypt"
                >
                  {isDownloading ? (
                    <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
                  ) : (
                    <Download className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                  )}
                </button>
              )}

              <button
                onClick={() => handleDeleteFile(fileShare.fileId)}
                className="p-2 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                title="Delete"
              >
                <Trash2 className="w-4 h-4 text-red-600 dark:text-red-400" />
              </button>
            </div>
          </div>
        )
      })}
    </div>
  )
}
