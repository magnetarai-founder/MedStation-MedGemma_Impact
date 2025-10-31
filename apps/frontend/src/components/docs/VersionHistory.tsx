/**
 * Version History Component
 *
 * Git-style version history viewer with restore functionality
 * Shows all versions of a file with timestamps, authors, and change descriptions
 */

import { useState } from 'react'
import { History, RotateCcw, Eye, Calendar, User, FileText, ChevronRight } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'

interface FileVersion {
  version_id: string
  version_number: number
  file_id: string
  user_id: string
  user_name: string
  changes_description: string
  created_at: string
  is_current: boolean
}

interface VersionHistoryProps {
  fileId: string
  onVersionRestore?: (versionNumber: number) => void
}

export function VersionHistory({ fileId, onVersionRestore }: VersionHistoryProps) {
  const [selectedVersion, setSelectedVersion] = useState<FileVersion | null>(null)
  const [isPreviewOpen, setIsPreviewOpen] = useState(false)
  const queryClient = useQueryClient()

  // Fetch version history
  const { data: versions = [], isLoading } = useQuery<FileVersion[]>({
    queryKey: ['version-history', fileId],
    queryFn: async () => {
      // TODO: Replace with actual API call
      // const response = await fetch(`/api/v1/files/${fileId}/versions`)
      // return await response.json()

      // Mock data
      return [
        {
          version_id: '1',
          version_number: 5,
          file_id: fileId,
          user_id: 'user_1',
          user_name: 'Field Worker',
          changes_description: 'Updated introduction section with latest data',
          created_at: new Date().toISOString(),
          is_current: true,
        },
        {
          version_id: '2',
          version_number: 4,
          file_id: fileId,
          user_id: 'user_2',
          user_name: 'Sarah Chen',
          changes_description: 'Fixed typos and formatting issues',
          created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
          is_current: false,
        },
        {
          version_id: '3',
          version_number: 3,
          file_id: fileId,
          user_id: 'user_3',
          user_name: 'Mike Rodriguez',
          changes_description: 'Added new requirements section',
          created_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
          is_current: false,
        },
        {
          version_id: '4',
          version_number: 2,
          file_id: fileId,
          user_id: 'user_1',
          user_name: 'Field Worker',
          changes_description: 'Initial draft of technical specifications',
          created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
          is_current: false,
        },
        {
          version_id: '5',
          version_number: 1,
          file_id: fileId,
          user_id: 'user_1',
          user_name: 'Field Worker',
          changes_description: 'Created document',
          created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
          is_current: false,
        },
      ]
    },
  })

  // Restore version mutation
  const restoreVersionMutation = useMutation({
    mutationFn: async (versionNumber: number) => {
      // TODO: Replace with actual API call
      // await fetch(`/api/v1/files/${fileId}/versions/${versionNumber}/restore`, {
      //   method: 'POST'
      // })
      await new Promise(resolve => setTimeout(resolve, 1000))
      return versionNumber
    },
    onSuccess: (versionNumber) => {
      queryClient.invalidateQueries({ queryKey: ['version-history', fileId] })
      queryClient.invalidateQueries({ queryKey: ['file-content', fileId] })
      toast.success(`Restored to version ${versionNumber}`)
      onVersionRestore?.(versionNumber)
    },
    onError: () => {
      toast.error('Failed to restore version')
    },
  })

  function handleRestoreVersion(version: FileVersion) {
    if (version.is_current) {
      toast.error('This is already the current version')
      return
    }

    if (
      !confirm(
        `Restore to version ${version.version_number}? Current version will be saved as a new version.`
      )
    ) {
      return
    }

    restoreVersionMutation.mutate(version.version_number)
  }

  function handleViewVersion(version: FileVersion) {
    setSelectedVersion(version)
    setIsPreviewOpen(true)
  }

  function formatDateTime(dateString: string) {
    const date = new Date(dateString)
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    })
  }

  function formatTimeAgo(dateString: string) {
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
    return `${Math.floor(diffDays / 7)}w ago`
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
        <History className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0" />
        <div>
          <h3 className="font-semibold text-blue-900 dark:text-blue-100">Version History</h3>
          <p className="text-sm text-blue-700 dark:text-blue-300">
            {versions.length} version{versions.length !== 1 ? 's' : ''} saved
          </p>
        </div>
      </div>

      {/* Version Timeline */}
      {versions.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <History className="w-12 h-12 mx-auto mb-3 text-gray-400" />
          <p className="text-gray-600 dark:text-gray-400">No version history available</p>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {versions.map((version, index) => (
              <div
                key={version.version_id}
                className={`p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors ${
                  version.is_current ? 'bg-blue-50 dark:bg-blue-900/10' : ''
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  {/* Version Info */}
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      {/* Version Number Badge */}
                      <div
                        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                          version.is_current
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                        }`}
                      >
                        <FileText className="w-3 h-3" />
                        v{version.version_number}
                        {version.is_current && ' (Current)'}
                      </div>

                      {/* Timeline Connector */}
                      {index < versions.length - 1 && (
                        <div className="hidden md:block absolute left-[52px] top-[60px] w-px h-12 bg-gray-300 dark:bg-gray-600"></div>
                      )}
                    </div>

                    {/* User and Time */}
                    <div className="flex items-center gap-4 mb-2 text-sm text-gray-600 dark:text-gray-400">
                      <div className="flex items-center gap-1.5">
                        <User className="w-3 h-3" />
                        <span className="font-medium">{version.user_name}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Calendar className="w-3 h-3" />
                        <span>{formatTimeAgo(version.created_at)}</span>
                      </div>
                    </div>

                    {/* Change Description */}
                    <p className="text-sm text-gray-700 dark:text-gray-300">
                      {version.changes_description || '(no description)'}
                    </p>

                    {/* Full Timestamp */}
                    <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                      {formatDateTime(version.created_at)}
                    </p>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleViewVersion(version)}
                      className="p-2 text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400
                               hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
                      title="View version"
                    >
                      <Eye className="w-4 h-4" />
                    </button>

                    {!version.is_current && (
                      <button
                        onClick={() => handleRestoreVersion(version)}
                        disabled={restoreVersionMutation.isPending}
                        className="p-2 text-gray-600 dark:text-gray-400 hover:text-green-600 dark:hover:text-green-400
                                 hover:bg-green-50 dark:hover:bg-green-900/20 rounded-lg transition-colors
                                 disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Restore this version"
                      >
                        <RotateCcw className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Version Preview Modal */}
      {isPreviewOpen && selectedVersion && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-3xl w-full max-h-[80vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                    Version {selectedVersion.version_number}
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {formatDateTime(selectedVersion.created_at)}
                  </p>
                </div>
                <button
                  onClick={() => setIsPreviewOpen(false)}
                  className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300
                           hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                >
                  ✕
                </button>
              </div>

              <div className="mb-4 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  <strong>Author:</strong> {selectedVersion.user_name}
                </p>
                <p className="text-sm text-gray-700 dark:text-gray-300 mt-1">
                  <strong>Changes:</strong> {selectedVersion.changes_description}
                </p>
              </div>

              <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 font-mono text-sm">
                <p className="text-gray-600 dark:text-gray-400 italic">
                  [Version content would be displayed here]
                </p>
              </div>

              <div className="mt-4 flex items-center justify-end gap-2">
                <button
                  onClick={() => setIsPreviewOpen(false)}
                  className="px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600
                           text-gray-800 dark:text-gray-200 rounded-lg transition-colors"
                >
                  Close
                </button>
                {!selectedVersion.is_current && (
                  <button
                    onClick={() => {
                      handleRestoreVersion(selectedVersion)
                      setIsPreviewOpen(false)
                    }}
                    disabled={restoreVersionMutation.isPending}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors
                             disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    <RotateCcw className="w-4 h-4" />
                    Restore Version
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * Compact Version Badge
 *
 * Small badge showing current version number
 */
interface VersionBadgeProps {
  versionNumber: number
  onClick?: () => void
}

export function VersionBadge({ versionNumber, onClick }: VersionBadgeProps) {
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-700
               hover:bg-gray-200 dark:hover:bg-gray-600 rounded text-xs font-medium
               text-gray-700 dark:text-gray-300 transition-colors"
      title="View version history"
    >
      <History className="w-3 h-3" />
      v{versionNumber}
      <ChevronRight className="w-3 h-3" />
    </button>
  )
}
