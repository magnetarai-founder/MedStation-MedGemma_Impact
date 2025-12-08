/**
 * VersionHistoryModal - View and restore previous versions of files
 * Displays version timeline with restore capability
 */

import { X, GitBranch, RotateCcw } from 'lucide-react'
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'

interface FileVersion {
  id: string
  version_number: number
  file_size: number
  created_at: string
  comment?: string
}

interface VersionHistoryModalProps {
  isOpen: boolean
  onClose: () => void
  fileId?: string
  filename?: string
}

export function VersionHistoryModal({ isOpen, onClose, fileId, filename }: VersionHistoryModalProps) {
  const [fileVersions, setFileVersions] = useState<FileVersion[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(false)

  useEffect(() => {
    if (isOpen && fileId) {
      // Reset pagination when modal opens
      setFileVersions([])
      setOffset(0)
      setHasMore(false)
      fetchFileVersions(0)
    }
  }, [isOpen, fileId])

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

  async function fetchFileVersions(currentOffset: number = offset) {
    if (!fileId) return

    const isInitialLoad = currentOffset === 0
    if (isInitialLoad) {
      setIsLoading(true)
    } else {
      setIsLoadingMore(true)
    }

    try {
      const url = new URL(`/api/v1/vault/files/${fileId}/versions`, window.location.origin)
      url.searchParams.append('limit', '50')
      url.searchParams.append('offset', currentOffset.toString())

      const response = await fetch(url.toString(), {
        credentials: 'include'
      })

      if (!response.ok) {
        throw new Error('Failed to fetch versions')
      }

      const data = await response.json()
      const newVersions = data.versions || []
      setFileVersions(prev => currentOffset === 0 ? newVersions : [...prev, ...newVersions])
      setOffset(currentOffset + newVersions.length)
      setHasMore(data.has_more || false)
    } catch (error) {
      console.error('Failed to fetch file versions:', error)
      toast.error('Failed to load version history')
    } finally {
      setIsLoading(false)
      setIsLoadingMore(false)
    }
  }

  function handleLoadMore() {
    fetchFileVersions(offset)
  }

  async function handleRestoreVersion(versionId: string) {
    if (!confirm('Restore this version? Current version will be saved in history.')) {
      return
    }

    try {
      const response = await fetch(`/api/v1/vault/versions/${versionId}/restore`, {
        method: 'POST',
        credentials: 'include'
      })

      if (!response.ok) {
        throw new Error('Failed to restore version')
      }

      toast.success('Version restored successfully')
      // Reset pagination and reload
      setFileVersions([])
      setOffset(0)
      setHasMore(false)
      fetchFileVersions(0)
    } catch (error) {
      console.error('Failed to restore version:', error)
      toast.error('Failed to restore version')
    }
  }

  function formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`
  }

  if (!isOpen || !fileId) return null

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded-lg w-[700px] max-h-[80vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-gray-300 dark:border-zinc-700">
          <h3 className="text-lg font-semibold flex items-center gap-2 text-gray-900 dark:text-gray-100">
            <GitBranch className="w-5 h-5" />
            Version History - "{filename}"
          </h3>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {isLoading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
              <p className="text-sm text-gray-500 dark:text-zinc-500 mt-2">Loading versions...</p>
            </div>
          ) : fileVersions.length === 0 ? (
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
                  <div className="flex-1 min-w-0">
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
                      Size: {formatBytes(version.file_size)}
                    </div>
                  </div>
                  {index !== 0 && (
                    <button
                      onClick={() => handleRestoreVersion(version.id)}
                      className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm flex items-center gap-1 transition-colors flex-shrink-0"
                    >
                      <RotateCcw className="w-4 h-4" />
                      Restore
                    </button>
                  )}
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
