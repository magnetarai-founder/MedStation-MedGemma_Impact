import { useState } from 'react'
import { AlertTriangle } from 'lucide-react'

export default function DangerZoneTab() {
  const [confirmInputs, setConfirmInputs] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState<Record<string, boolean>>({})

  const handleAction = async (action: string, endpoint: string, confirmText: string, successMsg: string) => {
    if (confirmInputs[action] !== confirmText) return

    setLoading({ ...loading, [action]: true })
    try {
      const response = await fetch(endpoint, { method: 'POST' })
      if (!response.ok) throw new Error(`${action} failed`)

      alert(successMsg)
      if (action === 'uninstall' || action === 'factory-reset') {
        window.location.reload()
      }
    } catch (error) {
      console.error(`${action} failed:`, error)
      alert(`Failed to ${action}`)
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
