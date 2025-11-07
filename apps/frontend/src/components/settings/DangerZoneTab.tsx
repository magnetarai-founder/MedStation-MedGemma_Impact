import { useState, useEffect } from 'react'
import { AlertTriangle, HardDrive, CheckCircle } from 'lucide-react'
import toast from 'react-hot-toast'

interface Backup {
  name: string
  path: string
  size_bytes: number
  created_at: string
  checksum?: string
}

export default function DangerZoneTab() {
  const [confirmInputs, setConfirmInputs] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState<Record<string, boolean>>({})
  const [backups, setBackups] = useState<Backup[]>([])
  const [selectedBackup, setSelectedBackup] = useState<string | null>(null)
  const [backupPassphrase, setBackupPassphrase] = useState('')

  // Load backups on mount
  useEffect(() => {
    loadBackups()
  }, [])

  const loadBackups = async () => {
    try {
      const response = await fetch('/api/v1/backups/list')
      if (!response.ok) throw new Error('Failed to load backups')
      const data = await response.json()
      setBackups(data.backups || [])
    } catch (error) {
      console.error('Failed to load backups:', error)
    }
  }

  const handleCreateBackup = async () => {
    if (!backupPassphrase) {
      toast.error('Please enter a passphrase to encrypt the backup')
      return
    }

    setLoading({ ...loading, 'create-backup': true })
    try {
      const response = await fetch('/api/v1/backups/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ passphrase: backupPassphrase })
      })
      if (!response.ok) throw new Error('Failed to create backup')
      const data = await response.json()

      if (data.success) {
        toast.success('Backup created successfully')
        await loadBackups() // Refresh list
      } else {
        throw new Error(data.error || 'Backup creation failed')
      }
    } catch (error) {
      console.error('Create backup failed:', error)
      toast.error(`Failed to create backup: ${error}`)
    } finally {
      setLoading({ ...loading, 'create-backup': false })
    }
  }

  const handleVerifyBackup = async (backupName: string) => {
    if (!backupPassphrase) {
      toast.error('Please enter the passphrase to verify this backup')
      return
    }

    setLoading({ ...loading, `verify-${backupName}`: true })
    try {
      const response = await fetch('/api/v1/backups/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          backup_name: backupName,
          passphrase: backupPassphrase
        })
      })
      if (!response.ok) throw new Error('Failed to verify backup')
      const data = await response.json()

      if (data.valid) {
        toast.success('Backup verified successfully')
      } else {
        toast.error('Backup verification failed - file may be corrupted or wrong passphrase')
      }
    } catch (error) {
      console.error('Verify backup failed:', error)
      toast.error(`Failed to verify backup: ${error}`)
    } finally {
      setLoading({ ...loading, [`verify-${backupName}`]: false })
    }
  }

  const handleRestoreBackup = async (backupName: string) => {
    if (!backupPassphrase) {
      toast.error('Please enter the passphrase to restore this backup')
      return
    }

    if (!confirm(`⚠️ RESTORE BACKUP?\n\nThis will overwrite all current data with:\n${backupName}\n\nType "RESTORE" to confirm`)) {
      return
    }

    setLoading({ ...loading, `restore-${backupName}`: true })
    try {
      const response = await fetch('/api/v1/backups/restore', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          backup_name: backupName,
          passphrase: backupPassphrase
        })
      })
      if (!response.ok) throw new Error('Failed to restore backup')
      const data = await response.json()

      if (data.success) {
        toast.success('Backup restored successfully - reloading...')
        setTimeout(() => window.location.reload(), 2000)
      } else {
        throw new Error('Restore failed')
      }
    } catch (error) {
      console.error('Restore backup failed:', error)
      toast.error(`Failed to restore backup: ${error}`)
    } finally {
      setLoading({ ...loading, [`restore-${backupName}`]: false })
    }
  }

  const handleCleanupBackups = async () => {
    setLoading({ ...loading, 'cleanup-backups': true })
    try {
      const response = await fetch('/api/v1/backups/cleanup', { method: 'POST' })
      if (!response.ok) throw new Error('Failed to cleanup backups')
      const data = await response.json()

      toast.success(`Deleted ${data.deleted_count} old backup(s)`)
      await loadBackups() // Refresh list
    } catch (error) {
      console.error('Cleanup backups failed:', error)
      toast.error(`Failed to cleanup backups: ${error}`)
    } finally {
      setLoading({ ...loading, 'cleanup-backups': false })
    }
  }

  const handleDownloadBackup = async (backupName: string) => {
    try {
      const response = await fetch(`/api/v1/backups/download?backup_name=${encodeURIComponent(backupName)}`)
      if (!response.ok) throw new Error('Failed to download backup')

      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = backupName
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      toast.success('Backup downloaded successfully')
    } catch (error) {
      console.error('Download backup failed:', error)
      toast.error(`Failed to download backup: ${error}`)
    }
  }

  const handleAction = async (action: string, endpoint: string, confirmText: string, successMsg: string) => {
    if (confirmInputs[action] !== confirmText) return

    setLoading({ ...loading, [action]: true })
    try {
      const response = await fetch(endpoint, { method: 'POST' })
      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Unknown error')
        toast.error(`${action} failed: ${errorText}`)
        throw new Error(`${action} failed`)
      }

      // Handle export actions (download files)
      if (action.startsWith('export-')) {
        const blob = await response.blob()
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `${action}-${new Date().toISOString().split('T')[0]}.${action === 'export-all' ? 'zip' : 'json'}`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
        toast.success(successMsg)
      } else {
        toast.success(successMsg)
      }

      if (action === 'uninstall' || action === 'factory-reset') {
        window.location.reload()
      }
    } catch (error) {
      console.error(`${action} failed:`, error)
      toast.error(`Failed to ${action}`)
    } finally {
      setLoading({ ...loading, [action]: false })
      setConfirmInputs({ ...confirmInputs, [action]: '' })
    }
  }

  const DangerButton = ({
    action,
    endpoint,
    title,
    description,
    details,
    confirmText = 'CONFIRM',
    severity = 'medium'
  }: {
    action: string
    endpoint: string
    title: string
    description: string
    details?: string
    confirmText?: string
    severity?: 'safe' | 'medium' | 'high' | 'nuclear'
  }) => {
    const colors = {
      safe: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800 text-blue-900 dark:text-blue-100',
      medium: 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800 text-orange-900 dark:text-orange-100',
      high: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-900 dark:text-red-100',
      nuclear: 'bg-red-100 dark:bg-red-950/40 border-red-300 dark:border-red-900 text-red-950 dark:text-red-50'
    }

    const buttonColors = {
      safe: 'bg-blue-600 hover:bg-blue-700',
      medium: 'bg-orange-600 hover:bg-orange-700',
      high: 'bg-red-600 hover:bg-red-700',
      nuclear: 'bg-red-700 hover:bg-red-800'
    }

    return (
      <div className={`border-2 rounded-lg p-4 ${colors[severity]}`}>
        <h4 className="font-semibold mb-1 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          {title}
        </h4>
        <p className="text-sm mb-2">{description}</p>
        {details && <p className="text-xs opacity-80 mb-3">{details}</p>}

        <div className="flex gap-2">
          <input
            type="text"
            value={confirmInputs[action] || ''}
            onChange={(e) => setConfirmInputs({ ...confirmInputs, [action]: e.target.value })}
            placeholder={confirmText}
            className="flex-1 px-3 py-1.5 text-sm border-2 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border-gray-300 dark:border-gray-700"
          />
          <button
            onClick={() => handleAction(action, endpoint, confirmText, `${title} completed successfully`)}
            disabled={confirmInputs[action] !== confirmText || loading[action]}
            className={`px-4 py-1.5 text-sm text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors ${buttonColors[severity]}`}
          >
            {loading[action] ? 'Processing...' : 'Execute'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Export & Backup - Safe */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-blue-500"></span>
          Export & Backup
        </h3>
        <div className="space-y-3">
          <DangerButton
            action="export-all"
            endpoint="/api/admin/export-all"
            title="Export All Data"
            description="Download complete backup as ZIP"
            details="Includes: AI chats, team messages, query library, settings, and uploaded files"
            severity="safe"
          />
          <DangerButton
            action="export-chats"
            endpoint="/api/admin/export-chats"
            title="Export AI Chat History"
            description="Download all AI conversations as JSON"
            details="Preserves: messages, timestamps, models used, and file attachments"
            severity="safe"
          />
          <DangerButton
            action="export-queries"
            endpoint="/api/admin/export-queries"
            title="Export Query Library"
            description="Download saved SQL queries as JSON"
            details="Preserves: query names, folders, tags, and descriptions"
            severity="safe"
          />
        </div>
      </div>

      {/* Local Backups - Safe */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-500"></span>
          <HardDrive className="w-5 h-5" />
          Local Backups
        </h3>

        <div className="space-y-4">
          {/* Passphrase Field */}
          <div className="bg-gray-50 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Backup Passphrase (encrypted at ~/.elohimos_backups)
            </label>
            <input
              type="password"
              value={backupPassphrase}
              onChange={(e) => setBackupPassphrase(e.target.value)}
              placeholder="Enter passphrase for backup encryption"
              className="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600
                       rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Used for create, verify, and restore operations. Keep this secure!
            </p>
          </div>

          {/* Create Backup Button */}
          <div className="bg-green-50 dark:bg-green-900/20 border-2 border-green-200 dark:border-green-800 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-semibold text-green-900 dark:text-green-100 mb-1">
                  Create New Backup
                </h4>
                <p className="text-sm text-green-700 dark:text-green-300">
                  Create encrypted backup of all databases locally
                </p>
              </div>
              <button
                onClick={handleCreateBackup}
                disabled={loading['create-backup'] || !backupPassphrase}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading['create-backup'] ? 'Creating...' : 'Create Backup'}
              </button>
            </div>
          </div>

          {/* Cleanup Old Backups */}
          <div className="bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-semibold text-blue-900 dark:text-blue-100 mb-1">
                  Cleanup Old Backups
                </h4>
                <p className="text-sm text-blue-700 dark:text-blue-300">
                  Delete backups older than 7 days (retention policy)
                </p>
              </div>
              <button
                onClick={handleCleanupBackups}
                disabled={loading['cleanup-backups']}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading['cleanup-backups'] ? 'Cleaning...' : 'Cleanup'}
              </button>
            </div>
          </div>

          {/* Backup List */}
          {backups.length > 0 && (
            <div className="bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
                <h4 className="font-semibold text-gray-900 dark:text-gray-100">
                  Available Backups ({backups.length})
                </h4>
              </div>
              <div className="divide-y divide-gray-200 dark:divide-gray-700">
                {backups.map((backup) => (
                  <div key={backup.name} className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="font-medium text-gray-900 dark:text-gray-100 mb-1">
                          {backup.name}
                        </div>
                        <div className="text-sm text-gray-600 dark:text-gray-400">
                          Size: {(backup.size_bytes / (1024 * 1024)).toFixed(2)} MB
                          {backup.created_at && ` • Created: ${new Date(backup.created_at).toLocaleString()}`}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleDownloadBackup(backup.name)}
                          className="px-3 py-1.5 text-sm bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors"
                          title="Download encrypted backup file"
                        >
                          Download
                        </button>
                        <button
                          onClick={() => handleVerifyBackup(backup.name)}
                          disabled={loading[`verify-${backup.name}`]}
                          className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                          {loading[`verify-${backup.name}`] ? 'Verifying...' : 'Verify'}
                        </button>
                        <button
                          onClick={() => handleRestoreBackup(backup.name)}
                          disabled={loading[`restore-${backup.name}`]}
                          className="px-3 py-1.5 text-sm bg-orange-600 hover:bg-orange-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                          {loading[`restore-${backup.name}`] ? 'Restoring...' : 'Restore'}
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {backups.length === 0 && (
            <div className="bg-gray-50 dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-700 rounded-lg p-8 text-center">
              <HardDrive className="w-12 h-12 mx-auto mb-3 text-gray-400" />
              <p className="text-gray-600 dark:text-gray-400 mb-2">No backups found</p>
              <p className="text-sm text-gray-500 dark:text-gray-500">
                Create your first backup to secure your data
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Data Management - Medium Risk */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-orange-500"></span>
          Data Management
        </h3>
        <div className="space-y-3">
          <DangerButton
            action="clear-chats"
            endpoint="/api/admin/clear-chats"
            title="Clear AI Chat History"
            description="Delete all AI conversations"
            details="Preserves: settings and query library"
            severity="medium"
          />
          <DangerButton
            action="clear-team"
            endpoint="/api/admin/clear-team-messages"
            title="Clear Team Messages"
            description="Delete P2P chat history"
            details="Preserves: AI chats and query library"
            severity="medium"
          />
          <DangerButton
            action="clear-library"
            endpoint="/api/admin/clear-query-library"
            title="Clear Query Library"
            description="Delete all saved SQL queries"
            details="Preserves: query execution history"
            severity="medium"
          />
          <DangerButton
            action="clear-history"
            endpoint="/api/admin/clear-query-history"
            title="Clear Query History"
            description="Delete SQL execution history"
            details="Preserves: saved queries in library"
            severity="medium"
          />
          <DangerButton
            action="clear-temp"
            endpoint="/api/admin/clear-temp-files"
            title="Clear Temp Files"
            description="Delete uploaded files and exports"
            details="Frees up disk space without affecting data"
            severity="medium"
          />
          <DangerButton
            action="clear-code"
            endpoint="/api/admin/clear-code-files"
            title="Clear Code Editor Files"
            description="Delete saved code snippets"
            details="Preserves: all other data"
            severity="medium"
          />
        </div>
      </div>

      {/* Reset Options - High Risk */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-red-500"></span>
          Reset Options
        </h3>
        <div className="space-y-3">
          <DangerButton
            action="reset-settings"
            endpoint="/api/admin/reset-settings"
            title="Reset All Settings"
            description="Restore default settings"
            details="Preserves: all data (chats, queries, files)"
            confirmText="RESET"
            severity="high"
          />
          <DangerButton
            action="reset-data"
            endpoint="/api/admin/reset-data"
            title="Reset All Data"
            description="Delete all data, keep settings"
            details="Deletes: chats, queries, history, temp files"
            confirmText="DELETE"
            severity="high"
          />
          <DangerButton
            action="factory-reset"
            endpoint="/api/admin/reset-all"
            title="Factory Reset"
            description="Complete wipe - like first install"
            details="Deletes: everything (data + settings)"
            confirmText="DELETE"
            severity="high"
          />
        </div>
      </div>

      {/* Nuclear Options - Destructive */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-red-700"></span>
          Nuclear Options
        </h3>
        <div className="space-y-3">
          <DangerButton
            action="uninstall"
            endpoint="/api/admin/uninstall"
            title="Uninstall Application"
            description="Remove all app data permanently"
            details="Moves data to Trash/Recycle Bin. Cannot be undone."
            confirmText="DELETE"
            severity="nuclear"
          />
        </div>
      </div>
    </div>
  )
}
