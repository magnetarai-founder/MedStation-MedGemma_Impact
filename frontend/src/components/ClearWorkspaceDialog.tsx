import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { useSessionStore } from '@/stores/sessionStore'
import { useLogsStore } from '@/stores/logsStore'
import { useJsonStore } from '@/stores/jsonStore'

export function ClearWorkspaceDialog() {
  const [open, setOpen] = useState(false)
  const { sessionId, isExecuting, setSessionId, setIsExecuting, clearSession } = useSessionStore()
  const { clearLogs } = useLogsStore()
  const { setConversionResult, setJsonFileData, setJsonContent, setActualJsonContent } = useJsonStore()

  useEffect(() => {
    const openHandler = () => setOpen(true)
    window.addEventListener('open-clear-workspace', openHandler)
    return () => window.removeEventListener('open-clear-workspace', openHandler)
  }, [])

  const handleClearWorkspace = async () => {
    if (isExecuting) {
      alert('Cannot clear while a query is running')
      return
    }

    try {
      setIsExecuting(true)

      // Delete current session on backend
      if (sessionId) {
        try { await api.deleteSession(sessionId) } catch {}
      }

      // Reset client state
      clearSession()
      clearLogs()

      // Clear JSON state
      setConversionResult(null)
      setJsonFileData(null)
      const defaultContent = `{
  "example": "Paste your JSON here",
  "array": [1, 2, 3],
  "nested": {
    "key": "value"
  }
}`
      setJsonContent(defaultContent)
      setActualJsonContent(defaultContent)

      // Clear editors
      try { window.dispatchEvent(new CustomEvent('sql-file-loaded', { detail: '' })) } catch {}
      try { window.dispatchEvent(new CustomEvent('clear-code-editor')) } catch {}

      // Create fresh session
      const s = await api.createSession()
      setSessionId(s.session_id)

      setOpen(false)
    } catch (e: any) {
      console.error('Clear workspace failed', e)
      alert('Failed to clear workspace')
    } finally {
      setIsExecuting(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Clear Workspace?</h2>

        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          You are about to clear your entire workspace. This will:
        </p>

        <ul className="text-sm text-gray-600 dark:text-gray-400 mb-6 space-y-2 list-disc list-inside">
          <li>Delete current session</li>
          <li>Clear uploaded files</li>
          <li>Remove query results</li>
          <li>Reset all editors</li>
        </ul>

        <p className="text-sm font-medium text-red-600 dark:text-red-400 mb-6">
          This cannot be undone.
        </p>

        <div className="flex justify-end space-x-3">
          <button
            onClick={() => setOpen(false)}
            className="px-4 py-2 text-sm rounded bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700"
            disabled={isExecuting}
          >
            Cancel
          </button>
          <button
            onClick={handleClearWorkspace}
            disabled={isExecuting}
            className={`px-4 py-2 text-sm rounded text-white ${
              isExecuting
                ? 'bg-red-400 cursor-not-allowed'
                : 'bg-red-600 hover:bg-red-700'
            }`}
          >
            {isExecuting ? 'Clearing...' : 'Clear Workspace'}
          </button>
        </div>
      </div>
    </div>
  )
}
