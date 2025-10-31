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
  id: string
  created_at: string
  size: number
  backup_type: 'manual' | 'automatic'
  status: 'completed' | 'in_progress' | 'failed'
  version: string
}

export default function BackupsTab() {
  const queryClient = useQueryClient()

  // Fetch backups
  const { data: backups = [], isLoading } = useQuery({
    queryKey: ['backups'],
    queryFn: async () => {
      // TODO: Replace with actual API call when backend is ready
      // const response = await fetch('/api/v1/backup/list')
      // const data = await response.json()
      // return data as Backup[]

      // Mock data for now
      return [
        {
          id: '1',
          created_at: new Date().toISOString(),
          size: 125000000, // 125 MB
          backup_type: 'manual' as const,
          status: 'completed' as const,
          version: '1.0.0',
        },
        {
          id: '2',
          created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
          size: 123500000, // 123.5 MB
          backup_type: 'automatic' as const,
          status: 'completed' as const,
          version: '1.0.0',
        },
        {
          id: '3',
          created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
          size: 120000000, // 120 MB
          backup_type: 'automatic' as const,
          status: 'completed' as const,
          version: '1.0.0',
        },
      ] as Backup[]
    },
  })

  // Create backup mutation
  const createBackupMutation = useMutation({
    mutationFn: async () => {
      // TODO: Replace with actual API call
      // await fetch('/api/v1/backup/create', { method: 'POST' })

      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 2000))
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backups'] })
      toast.success('Backup created successfully')
    },
    onError: (error) => {
      console.error('Failed to create backup:', error)
      toast.error('Failed to create backup')
    },
  })

  // Restore backup mutation
  const restoreBackupMutation = useMutation({
    mutationFn: async (backupId: string) => {
      // TODO: Replace with actual API call
      // await fetch(`/api/v1/backup/restore/${backupId}`, { method: 'POST' })

      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 3000))
      return backupId
    },
    onSuccess: () => {
      toast.success('Backup restored successfully. Please reload the application.', {
        duration: 10000,
      })
    },
    onError: (error) => {
      console.error('Failed to restore backup:', error)
      toast.error('Failed to restore backup')
    },
  })

  // Delete backup mutation
  const deleteBackupMutation = useMutation({
    mutationFn: async (backupId: string) => {
      // TODO: Replace with actual API call
      // await fetch(`/api/v1/backup/${backupId}`, { method: 'DELETE' })

      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000))
      return backupId
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backups'] })
      toast.success('Backup deleted')
    },
    onError: (error) => {
      console.error('Failed to delete backup:', error)
      toast.error('Failed to delete backup')
    },
  })

  function handleCreateBackup() {
    if (!confirm('Create a new backup? This may take a few moments.')) {
      return
    }

    createBackupMutation.mutate()
  }

  function handleRestoreBackup(backup: Backup) {
    if (!confirm(
      `Restore from backup created on ${formatDate(backup.created_at)}? This will overwrite current data and cannot be undone.`
    )) {
      return
    }

    restoreBackupMutation.mutate(backup.id)
  }

  function handleDeleteBackup(backup: Backup) {
    if (!confirm(`Delete backup from ${formatDate(backup.created_at)}? This cannot be undone.`)) {
      return
    }

    deleteBackupMutation.mutate(backup.id)
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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  return (
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
          disabled={createBackupMutation.isPending}
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
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Size
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {backups.map((backup) => (
                  <tr
                    key={backup.id}
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
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                          backup.backup_type === 'manual'
                            ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400'
                            : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                        }`}
                      >
                        {backup.backup_type === 'manual' ? 'Manual' : 'Automatic'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1.5 text-sm text-gray-600 dark:text-gray-400">
                        <HardDrive className="w-4 h-4" />
                        {formatBytes(backup.size)}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400">
                        <CheckCircle className="w-3 h-3" />
                        Completed
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleRestoreBackup(backup)}
                          disabled={restoreBackupMutation.isPending}
                          className="p-2 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20
                                   rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          title="Restore backup"
                        >
                          <RotateCcw className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteBackup(backup)}
                          disabled={deleteBackupMutation.isPending}
                          className="p-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20
                                   rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          title="Delete backup"
                        >
                          <Trash2 className="w-4 h-4" />
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
              <li>• Backups are stored locally and retained for 7 days</li>
              <li>• Restoring a backup will overwrite all current data</li>
              <li>• Create manual backups before major changes</li>
              <li>• Export backups to external storage for long-term retention</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
