/**
 * StorageDashboardModal - Display vault storage statistics
 * Shows total files, total size, breakdown by type, and largest files
 */

import { X, HardDrive, File } from 'lucide-react'
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'

interface StorageStats {
  total_files: number
  total_size: number
  breakdown: Array<{
    category: string
    count: number
    size: number
  }>
  largest_files?: Array<{
    id: string
    filename: string
    file_size: number
  }>
}

interface StorageDashboardModalProps {
  isOpen: boolean
  onClose: () => void
}

export function StorageDashboardModal({ isOpen, onClose }: StorageDashboardModalProps) {
  const [storageStats, setStorageStats] = useState<StorageStats | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (isOpen) {
      fetchStorageStats()
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

  async function fetchStorageStats() {
    setIsLoading(true)
    try {
      const response = await fetch('/api/v1/vault/storage/stats', {
        credentials: 'include'
      })

      if (!response.ok) {
        throw new Error('Failed to fetch storage stats')
      }

      const data = await response.json()
      setStorageStats(data)
    } catch (error) {
      console.error('Failed to fetch storage stats:', error)
      toast.error('Failed to load storage statistics')
    } finally {
      setIsLoading(false)
    }
  }

  function formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-900 rounded-lg max-w-2xl w-full">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <HardDrive className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Storage Statistics
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-6 max-h-[70vh] overflow-y-auto">
          {isLoading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">Loading storage statistics...</p>
            </div>
          ) : storageStats ? (
            <>
              {/* Summary Stats */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
                  <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">Total Files</div>
                  <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                    {storageStats.total_files.toLocaleString()}
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
              {storageStats.breakdown && storageStats.breakdown.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                    Storage by File Type
                  </h4>
                  <div className="space-y-3">
                    {storageStats.breakdown.map((item) => {
                      const percentage = storageStats.total_size > 0
                        ? (item.size / storageStats.total_size * 100).toFixed(1)
                        : '0'

                      const colors: Record<string, string> = {
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
              )}

              {/* Largest Files */}
              {storageStats.largest_files && storageStats.largest_files.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                    Largest Files
                  </h4>
                  <div className="space-y-2">
                    {storageStats.largest_files.map((file) => (
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
              No storage data available
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 p-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
