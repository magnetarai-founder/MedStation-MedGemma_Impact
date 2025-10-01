import { useEffect, useRef, useState } from 'react'
import { Terminal, Trash2 } from 'lucide-react'
import { useLogsStore, LogEntry } from '@/stores/logsStore'

export function LogViewer() {
  const { logs, appendLog, clearLogs } = useLogsStore()
  const [autoScroll, setAutoScroll] = useState(true)
  const logsEndRef = useRef<HTMLDivElement>(null)

  // Auto scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, autoScroll])

  // Listen for log events
  useEffect(() => {
    const handleLog = (event: CustomEvent<LogEntry>) => {
      appendLog(event.detail)
    }

    // Commented out console hijacking - it can cause performance issues and freezing
    // when switching tabs during heavy operations
    /*
    const originalLog = console.log
    const originalError = console.error
    const originalWarn = console.warn

    console.log = (...args) => {
      originalLog(...args)
      appendLog({ id: Date.now().toString(), timestamp: new Date().toLocaleTimeString(), level: 'info', message: args.join(' ') })
    }

    console.error = (...args) => {
      originalError(...args)
      appendLog({ id: Date.now().toString(), timestamp: new Date().toLocaleTimeString(), level: 'error', message: args.join(' ') })
    }

    console.warn = (...args) => {
      originalWarn(...args)
      appendLog({ id: Date.now().toString(), timestamp: new Date().toLocaleTimeString(), level: 'warning', message: args.join(' ') })
    }
    */

    window.addEventListener('app-log', handleLog as EventListener)

    return () => {
      /*
      console.log = originalLog
      console.error = originalError
      console.warn = originalWarn
      */
      window.removeEventListener('app-log', handleLog as EventListener)
    }
  }, [])

  const clearLogsLocal = () => {
    if (window.confirm('Clear all logs?')) clearLogs()
  }

  const getLevelColor = (level: LogEntry['level']) => {
    switch (level) {
      case 'error': return 'text-red-600 dark:text-red-400'
      case 'warning': return 'text-yellow-600 dark:text-yellow-400'
      case 'success': return 'text-green-600 dark:text-green-400'
      default: return 'text-gray-600 dark:text-gray-400'
    }
  }

  if (logs.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500">
        <Terminal className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No logs yet</p>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Log controls */}
      <div className="flex items-center justify-between p-2 border-b border-gray-200 dark:border-gray-800">
        <label className="flex items-center text-xs text-gray-600 dark:text-gray-400">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => setAutoScroll(e.target.checked)}
            className="mr-1"
          />
          Auto-scroll
        </label>
        <button
          onClick={clearLogsLocal}
          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
          title="Clear logs"
        >
          <Trash2 className="w-4 h-4 text-gray-500" />
        </button>
      </div>

      {/* Log entries */}
      <div className="flex-1 overflow-auto p-2 font-mono text-xs">
        {logs.map((log) => (
          <div key={log.id} className="flex py-0.5 hover:bg-gray-50 dark:hover:bg-gray-900">
            <span className="text-gray-500 dark:text-gray-500 mr-2">{log.timestamp}</span>
            <span className={`uppercase mr-2 ${getLevelColor(log.level)}`}>
              [{log.level}]
            </span>
            <span className="text-gray-700 dark:text-gray-300 break-all">{log.message}</span>
          </div>
        ))}
        <div ref={logsEndRef} />
      </div>
    </div>
  )
}
