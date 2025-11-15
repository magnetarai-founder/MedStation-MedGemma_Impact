/**
 * TrashBinModal - Manage deleted files in trash
 * View, restore, or permanently delete files from trash
 */

import { X, Trash2, RotateCcw, File } from 'lucide-react'
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'

interface TrashFile {
  id: string
  filename: string
  deleted_at: string
  file_size?: number
  folder_path?: string
}

interface TrashBinModalProps {
  isOpen: boolean
  onClose: () => void
}

export function TrashBinModal({ isOpen, onClose }: TrashBinModalProps) {
  const [trashFiles, setTrashFiles] = useState<TrashFile[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(false)

  useEffect(() => {
    if (isOpen) {
      // Reset pagination when modal opens
      setTrashFiles([])
      setOffset(0)
      setHasMore(false)
      fetchTrashFiles(0)
    }
  }, [isOpen])

  // Handle Escape key to close modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [onClose])

  async function fetchTrashFiles(currentOffset: number = offset) {
    const isInitialLoad = currentOffset === 0
    if (isInitialLoad) {
      setIsLoading(true)
    } else {
      setIsLoadingMore(true)
    }

    try {
      const url = new URL('/api/v1/vault/trash', window.location.origin)
      url.searchParams.append('vault_type', 'real')
      url.searchParams.append('limit', '50')
      url.searchParams.append('offset', currentOffset.toString())

      const response = await fetch(url.toString(), {
        credentials: 'include'
      })

      if (!response.ok) {
        throw new Error('Failed to fetch trash files')
      }

      const data = await response.json()
      const newFiles = data.trash_files || []
      setTrashFiles(prev => currentOffset === 0 ? newFiles : [...prev, ...newFiles])
      setOffset(currentOffset + newFiles.length)
      setHasMore(data.has_more || false)
    } catch (error) {
      console.error('Failed to fetch trash files:', error)
      toast.error('Failed to load trash')
    } finally {
      setIsLoading(false)
      setIsLoadingMore(false)
    }
  }

  function handleLoadMore() {
    fetchTrashFiles(offset)
  }

  async function handleRestoreFromTrash(fileId: string) {
    try {
      const response = await fetch(`/api/v1/vault/trash/restore/${fileId}`, {
        method: 'POST',
        credentials: 'include'
      })

      if (!response.ok) {
        throw new Error('Failed to restore file')
      }

      toast.success('File restored successfully')
      // Reset pagination and reload
      setTrashFiles([])
      setOffset(0)
      setHasMore(false)
      fetchTrashFiles(0)
    } catch (error) {
      console.error('Failed to restore file:', error)
      toast.error('Failed to restore file')
    }
  }

  async function handleEmptyTrash() {
    if (!confirm('Permanently delete all files in trash? This cannot be undone.')) {
      return
    }

    try {
      const response = await fetch('/api/v1/vault/trash/empty', {
        method: 'POST',
        credentials: 'include'
      })

      if (!response.ok) {
        throw new Error('Failed to empty trash')
      }

      toast.success('Trash emptied successfully')
      setTrashFiles([])
      setOffset(0)
      setHasMore(false)
    } catch (error) {
      console.error('Failed to empty trash:', error)
      toast.error('Failed to empty trash')
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded-lg w-[800px] max-h-[80vh] overflow-hidden flex flex-col">
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
                className="px-3 py-1 text-sm bg-red-600 hover:bg-red-700 text-white rounded transition-colors"
              >
                Empty Trash
              </button>
            )}
            <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors">
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {isLoading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
              <p className="text-sm text-gray-500 dark:text-zinc-500 mt-2">Loading trash...</p>
            </div>
          ) : trashFiles.length === 0 ? (
            <div className="text-center py-12 text-gray-500 dark:text-zinc-500">
              <Trash2 className="w-16 h-16 mx-auto mb-4 opacity-20" />
              <p>Trash is empty</p>
            </div>
          ) : (
            <div className="space-y-2">
              {trashFiles.map((file) => (
                <div
                  key={file.id}
                  className="flex items-center gap-4 p-3 bg-gray-100 dark:bg-zinc-800 rounded border border-gray-300 dark:border-zinc-700 hover:border-gray-400 dark:hover:border-zinc-600 transition-colors"
                >
                  <File className="w-5 h-5 text-gray-500 dark:text-zinc-400 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-gray-900 dark:text-gray-100 truncate">{file.filename}</div>
                    <div className="text-sm text-gray-600 dark:text-zinc-500">
                      Deleted {new Date(file.deleted_at).toLocaleString()}
                    </div>
                  </div>
                  <button
                    onClick={() => handleRestoreFromTrash(file.id)}
                    className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm flex items-center gap-1 transition-colors flex-shrink-0"
                  >
                    <RotateCcw className="w-4 h-4" />
                    Restore
                  </button>
                </div>
              ))}

              {/* Load More Button */}
              {hasMore && (
                <div className="flex justify-center pt-2">
                  <button
                    onClick={handleLoadMore}
                    disabled={isLoadingMore}
                    className="px-4 py-2 bg-gray-200 dark:bg-zinc-700 hover:bg-gray-300 dark:hover:bg-zinc-600 disabled:opacity-50 disabled:cursor-not-allowed text-gray-900 dark:text-gray-100 rounded text-sm"
                  >
                    {isLoadingMore ? 'Loading...' : 'Load More'}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
