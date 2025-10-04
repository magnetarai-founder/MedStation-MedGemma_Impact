import { useEffect, useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import { api } from '@/lib/api'
import { useSessionStore } from '@/stores/sessionStore'
import { useEditorStore } from '@/stores/editorStore'
import { useJsonStore } from '@/stores/jsonStore'

export function ClearWorkspaceDialog() {
  const [open, setOpen] = useState(false)
  const { sessionId, isExecuting, setSessionId, setIsExecuting, clearSession } = useSessionStore()
  const { reset: resetEditor } = useEditorStore()
  const { setConversionResult, setJsonFileData, setJsonContent, setActualJsonContent } = useJsonStore()

  useEffect(() => {
    const openHandler = () => setOpen(true)
    window.addEventListener('open-clear-workspace', openHandler)
    return () => window.removeEventListener('open-clear-workspace', openHandler)
  }, [])

  const handleClearWorkspace = async () => {
    if (isExecuting) {
      alert('Cannot clear while processing')
      return
    }

    try {
      setIsExecuting(true)

      // Delete current session on backend
      if (sessionId) {
        try { await api.deleteSession(sessionId) } catch {}
      }

      // Reset all state EXCEPT logs
      clearSession()
      resetEditor()

      // Reset JSON state
      const defaultContent = `{
  "example": "Paste your JSON here",
  "array": [1, 2, 3],
  "nested": {
    "key": "value"
  }
}`
      setConversionResult(null)
      setJsonFileData(null)
      setJsonContent(defaultContent)
      setActualJsonContent(defaultContent)

      // Clear the code editor
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
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={() => setOpen(false)}
    >
      <div
        className="w-full max-w-md bg-white dark:bg-gray-900 rounded-lg shadow-xl border border-gray-200 dark:border-gray-800 p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start space-x-3 mb-4">
          <div className="flex-shrink-0">
            <AlertTriangle className="w-6 h-6 text-yellow-500" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Clear Data Workspace?
            </h2>
          </div>
        </div>

        <p className="text-sm text-gray-700 dark:text-gray-300 mb-3 ml-9">
          You're about to clear your current data workspace. This action will:
        </p>

        <ul className="text-sm text-gray-600 dark:text-gray-400 mb-4 ml-9 space-y-1.5">
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>Remove uploaded files and query results</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>Reset the code editor</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>Clear current session data</span>
          </li>
        </ul>

        <p className="text-sm text-gray-600 dark:text-gray-400 mb-6 ml-9 bg-blue-50 dark:bg-blue-950/30 border-l-2 border-blue-400 dark:border-blue-600 pl-3 py-2">
          Your query history and logs will be preserved and remain accessible in the History & Queries tabs.
        </p>

        <div className="flex justify-between items-center">
          <button
            onClick={() => setOpen(false)}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            disabled={isExecuting}
          >
            Cancel
          </button>
          <button
            onClick={handleClearWorkspace}
            disabled={isExecuting}
            className={`px-4 py-2 text-sm font-medium rounded-lg text-white transition-colors ${
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
