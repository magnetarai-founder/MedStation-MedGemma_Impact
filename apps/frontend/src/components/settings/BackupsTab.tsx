/**
 * Backups Tab Component
 *
 * Manage system backups with 7-day retention
 * Create manual backups and restore from previous backups
 */

import { useState, useEffect } from 'react'
import { Database, Download, RotateCcw, Trash2, Calendar, HardDrive, AlertTriangle, CheckCircle, Clock } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'

interface Backup {
  name: string
  size_bytes: number
  created_at: string
  checksum: string
}

interface PassphraseModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (passphrase: string) => void
  title: string
  description: string
  isLoading?: boolean
}

function PassphraseModal({ isOpen, onClose, onSubmit, title, description, isLoading }: PassphraseModalProps) {
  const [passphrase, setPassphrase] = useState('')

  if (!isOpen) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (passphrase) {
      onSubmit(passphrase)
      setPassphrase('')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
          {title}
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          {description}
        </p>
        <form onSubmit={handleSubmit}>
          <input
            type="password"
            value={passphrase}
            onChange={(e) => setPassphrase(e.target.value)}
            placeholder="Enter passphrase"
            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
                     bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
                     focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            autoFocus
            disabled={isLoading}
          />
          <div className="flex gap-3 mt-4">
            <button
              type="button"
              onClick={() => {
                setPassphrase('')
                onClose()
              }}
              disabled={isLoading}
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
                       text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700
                       transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!passphrase || isLoading}
              className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg
                       font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Processing...' : 'Confirm'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function BackupsTab() {
  const queryClient = useQueryClient()
  const [passphraseModal, setPassphraseModal] = useState<{
    isOpen: boolean
    action: 'create' | 'verify' | 'restore' | null
    backup?: Backup
  }>({
    isOpen: false,
    action: null
  })

  // Fetch backups
  const { data: backupsData, isLoading } = useQuery({
    queryKey: ['backups'],
    queryFn: async () => {
      const response = await fetch('/api/v1/backups/list', {
        credentials: 'include'
      })
      if (!response.ok) {
        throw new Error('Failed to fetch backups')
      }
      const data = await response.json()
      return data as { backups: Backup[]; total: number }
    },
  })

  const backups = backupsData?.backups || []

  // Create backup mutation
  const createBackupMutation = useMutation({
    mutationFn: async (passphrase: string) => {
      const response = await fetch('/api/v1/backups/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ passphrase })
      })

      const data = await response.json()

      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Failed to create backup')
      }

      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backups'] })
      toast.success('Backup created successfully')
      setPassphraseModal({ isOpen: false, action: null })
    },
    onError: (error: Error) => {
      console.error('Failed to create backup:', error)
      toast.error(`Failed to create backup: ${error.message}`)
    },
  })

  // Verify backup mutation
  const verifyBackupMutation = useMutation({
    mutationFn: async ({ backup, passphrase }: { backup: Backup; passphrase: string }) => {
      const response = await fetch('/api/v1/backups/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          backup_name: backup.name,
          passphrase
        })
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to verify backup')
      }

      return data
    },
    onSuccess: (data) => {
      if (data.valid) {
        toast.success('Backup verified successfully')
      } else {
        toast.error('Backup verification failed - invalid or corrupted')
      }
      setPassphraseModal({ isOpen: false, action: null })
    },
    onError: (error: Error) => {
      console.error('Failed to verify backup:', error)
      toast.error(`Failed to verify backup: ${error.message}`)
    },
  })

  // Restore backup mutation
  const restoreBackupMutation = useMutation({
    mutationFn: async ({ backup, passphrase }: { backup: Backup; passphrase: string }) => {
      const response = await fetch('/api/v1/backups/restore', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          backup_name: backup.name,
          passphrase
        })
      })

      const data = await response.json()

      if (!response.ok || !data.success) {
        throw new Error(data.detail || 'Failed to restore backup')
      }

      return data
    },
    onSuccess: () => {
      toast.success('Backup restored successfully. Please reload the application.', {
        duration: 10000,
      })
      setPassphraseModal({ isOpen: false, action: null })
    },
    onError: (error: Error) => {
      console.error('Failed to restore backup:', error)
      toast.error(`Failed to restore backup: ${error.message}`)
    },
  })

  function handleCreateBackup() {
    if (!confirm('Create a new backup? This may take a few moments.')) {
      return
    }

    setPassphraseModal({
      isOpen: true,
      action: 'create'
    })
  }

  function handleVerifyBackup(backup: Backup) {
    setPassphraseModal({
      isOpen: true,
      action: 'verify',
      backup
    })
  }

  function handleRestoreBackup(backup: Backup) {
    if (!confirm(
      `Restore from backup created on ${formatDate(backup.created_at)}? This will overwrite current data and cannot be undone.`
    )) {
      return
    }

    setPassphraseModal({
      isOpen: true,
      action: 'restore',
      backup
    })
  }

  function handleDownloadBackup(backup: Backup) {
    // Trigger download via anchor element
    const link = document.createElement('a')
    link.href = `/api/v1/backups/download?backup_name=${encodeURIComponent(backup.name)}`
    link.download = backup.name
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    toast.success('Downloading backup...')
  }

  function handlePassphraseSubmit(passphrase: string) {
    const { action, backup } = passphraseModal

    if (action === 'create') {
      createBackupMutation.mutate(passphrase)
    } else if (action === 'verify' && backup) {
      verifyBackupMutation.mutate({ backup, passphrase })
    } else if (action === 'restore' && backup) {
      restoreBackupMutation.mutate({ backup, passphrase })
    }
  }

  function formatDate(dateString: string) {
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

  function formatBytes(bytes: number) {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
  }

  function getTimeAgo(dateString: string) {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
  }

  const isProcessing = createBackupMutation.isPending || verifyBackupMutation.isPending || restoreBackupMutation.isPending

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  return (
    <>
      <div className="space-y-6">
        <div className="flex items-start gap-3 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <Database className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-blue-900 dark:text-blue-100 mb-1">
              System Backups
            </h4>
            <p className="text-sm text-blue-700 dark:text-blue-300">
              Backups include all documents, vault files, settings, and workflows. Automatic backups
              are created daily and retained for 7 days. You can also create manual backups anytime.
            </p>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Available Backups
          </h3>
          <button
            onClick={handleCreateBackup}
            disabled={isProcessing}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium
                     disabled:opacity-50 disabled:cursor-not-allowed transition-colors
                     flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            {createBackupMutation.isPending ? 'Creating...' : 'Backup Now'}
          </button>
        </div>

        {backups.length === 0 ? (
          <div className="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
            <Database className="w-12 h-12 mx-auto mb-3 text-gray-400" />
            <p className="text-gray-600 dark:text-gray-400">No backups found</p>
            <p className="text-sm text-gray-500 dark:text-gray-500 mt-1">
              Create your first backup to get started
            </p>
          </div>
        ) : (
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-700">
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Date Created
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Size
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {backups.map((backup) => (
                    <tr
                      key={backup.name}
                      className="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors"
                    >
                      <td className="px-6 py-4">
                        <div>
                          <div className="font-medium text-gray-900 dark:text-gray-100">
                            {formatDate(backup.created_at)}
                          </div>
                          <div className="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {getTimeAgo(backup.created_at)}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-600 dark:text-gray-400 font-mono">
                          {backup.name}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-1.5 text-sm text-gray-600 dark:text-gray-400">
                          <HardDrive className="w-4 h-4" />
                          {formatBytes(backup.size_bytes)}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleDownloadBackup(backup)}
                            className="p-2 text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20
                                     rounded-lg transition-colors"
                            title="Download backup"
                          >
                            <Download className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleVerifyBackup(backup)}
                            disabled={isProcessing}
                            className="p-2 text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-900/20
                                     rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Verify backup"
                          >
                            <CheckCircle className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleRestoreBackup(backup)}
                            disabled={isProcessing}
                            className="p-2 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20
                                     rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Restore backup"
                          >
                            <RotateCcw className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <div className="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm">
              <p className="font-semibold text-amber-900 dark:text-amber-100 mb-1">
                Important Backup Information
              </p>
              <ul className="text-amber-700 dark:text-amber-300 space-y-1">
                <li>• Backups are encrypted with your passphrase and stored locally</li>
                <li>• Backups are retained for 7 days</li>
                <li>• Restoring a backup will overwrite all current data</li>
                <li>• Create manual backups before major changes</li>
                <li>• Download backups to external storage for long-term retention</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <PassphraseModal
        isOpen={passphraseModal.isOpen}
        onClose={() => setPassphraseModal({ isOpen: false, action: null })}
        onSubmit={handlePassphraseSubmit}
        title={
          passphraseModal.action === 'create' ? 'Create Backup' :
          passphraseModal.action === 'verify' ? 'Verify Backup' :
          'Restore Backup'
        }
        description={
          passphraseModal.action === 'create'
            ? 'Enter a passphrase to encrypt your backup. You will need this passphrase to restore the backup later.'
            : passphraseModal.action === 'verify'
            ? 'Enter the passphrase used to create this backup to verify its integrity.'
            : 'Enter the passphrase used to create this backup to restore it.'
        }
        isLoading={isProcessing}
      />
    </>
  )
}
