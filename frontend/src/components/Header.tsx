import { Trash2, Zap } from 'lucide-react'
import { api } from '@/lib/api'
import { useSessionStore } from '@/stores/sessionStore'
import { useNavigationStore } from '@/stores/navigationStore'
import { useLogsStore } from '@/stores/logsStore'
import { useJsonStore } from '@/stores/jsonStore'

export function Header() {
  const { sessionId, isExecuting, setSessionId, setCurrentFile, setCurrentQuery, setIsExecuting, clearSession } = useSessionStore()
  const { activeTab } = useNavigationStore()
  const { clearLogs } = useLogsStore()
  const { setConversionResult, setJsonFileData, setJsonContent, setActualJsonContent } = useJsonStore()


  const handleClearSqlWorkspace = async () => {
    if (!window.confirm('Clear SQL workspace and reset session?')) return
    if (isExecuting) {
      console.error('Cannot clear while a query is running')
      alert('Cannot clear while a query is running')
      return
    }
    try {
      setIsExecuting(true)
      // Delete current session on backend
      if (sessionId) {
        try { await api.deleteSession(sessionId) } catch {}
      }
      // Reset SQL state only
      clearSession()
      clearLogs()

      // Clear SQL editor via existing event channel
      try { window.dispatchEvent(new CustomEvent('sql-file-loaded', { detail: '' })) } catch {}

      // Create a fresh session
      const s = await api.createSession()
      setSessionId(s.session_id)
    } catch (e: any) {
      console.error('Clear SQL workspace failed', e)
      alert('Failed to clear SQL workspace')
    } finally {
      setIsExecuting(false)
    }
  }

  const handleClearJsonWorkspace = async () => {
    if (!window.confirm('Clear JSON workspace?')) return
    if (isExecuting) {
      console.error('Cannot clear while processing')
      alert('Cannot clear while processing')
      return
    }
    try {
      setIsExecuting(true)

      // Clear JSON state only
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
      clearLogs()
    } catch (e: any) {
      console.error('Clear JSON workspace failed', e)
      alert('Failed to clear JSON workspace')
    } finally {
      setIsExecuting(false)
    }
  }

  return (
    <header className="glass border-b border-white/30 dark:border-gray-700/40">
      <div className="flex items-center justify-between py-3.5 px-6">
        {/* Title aligned after nav rail */}
        <h1 className="text-xl font-bold tracking-tight text-gray-900 dark:text-gray-100">
          OmniStudio
        </h1>

        {/* Right side - buttons */}
        <div className="flex items-center space-x-4">
          {/* Tab-specific Clear buttons */}
          {activeTab === 'sql' && (
            <button
              onClick={handleClearSqlWorkspace}
              disabled={isExecuting}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-xl text-sm transition-all ${isExecuting ? 'text-gray-400 cursor-not-allowed' : 'text-gray-700 hover:bg-red-50 hover:text-red-600 dark:text-gray-300 dark:hover:bg-red-900/20 dark:hover:text-red-400'}`}
              title="Clear SQL workspace"
            >
              <Trash2 className="w-4 h-4" />
              <span>Clear</span>
            </button>
          )}
          {activeTab === 'json' && (
            <button
              onClick={handleClearJsonWorkspace}
              disabled={isExecuting}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-xl text-sm transition-all ${isExecuting ? 'text-gray-400 cursor-not-allowed' : 'text-gray-700 hover:bg-red-50 hover:text-red-600 dark:text-gray-300 dark:hover:bg-red-900/20 dark:hover:text-red-400'}`}
              title="Clear JSON workspace"
            >
              <Trash2 className="w-4 h-4" />
              <span>Clear</span>
            </button>
          )}
        </div>
      </div>
    </header>
  )
}
