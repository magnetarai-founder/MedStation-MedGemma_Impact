import { useState, useCallback, useEffect, useRef } from 'react'
import Editor from '@monaco-editor/react'
import { Play, Square, Zap, Loader2, Download, Trash2 } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useSessionStore } from '@/stores/sessionStore'
import { useSettingsStore } from '@/stores/settingsStore'

// Helper to get the correct modifier key based on platform
const getModifierKey = () => {
  // Check multiple ways to detect Mac
  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0 ||
                navigator.userAgent.toUpperCase().indexOf('MAC') >= 0 ||
                (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1) // M1 iPads
  
  return isMac ? 'Cmd' : 'Ctrl'
}

export function SQLEditor() {
  const { sessionId, currentFile, setCurrentQuery, isExecuting, setIsExecuting } = useSessionStore()
  const { previewRowCount } = useSettingsStore()
  const [sql, setSql] = useState('SELECT * FROM excel_file LIMIT 100')
  const editorRef = useRef<any>(null)
  const monacoRef = useRef<any>(null)

  const queryMutation = useMutation({
    mutationFn: async (isPreview: boolean = false) => {
      if (!sessionId) throw new Error('No session')
      const limit = isPreview ? previewRowCount : null
      const result = await api.executeQuery(sessionId, sql, { limit })
      // Mark preview queries as not downloadable
      return { ...result, is_preview_only: isPreview }
    },
    onMutate: () => {
      // Set executing state when mutation starts
      setIsExecuting(true)
    },
    onSuccess: (data) => {
      setCurrentQuery(data)
    },
    onError: (error: any) => {
      console.error('Query failed:', error.response?.data?.detail || error)
    },
    onSettled: () => {
      // Always reset executing state when done
      setIsExecuting(false)
    },
  })

  const handleExecute = useCallback((isPreview: boolean = false) => {
    if (!currentFile) {
      console.error('Please load a file first')
      return
    }
    // Prevent multiple concurrent executions
    if (queryMutation.isPending) {
      console.warn('Query already executing, please wait...')
      return
    }
    // Clear previous results immediately to avoid showing stale data
    setCurrentQuery(null)
    queryMutation.mutate(isPreview)
  }, [currentFile, queryMutation, setCurrentQuery])

  const handleStop = useCallback(() => {
    // TODO: Implement query cancellation
    console.log('Query cancellation not yet implemented')
  }, [])

  // Insert column names/snippets at cursor on 'insert-sql' events
  useEffect(() => {
    const handler = (event: CustomEvent<string>) => {
      const text = event.detail
      try {
        const editor = editorRef.current
        const monaco = monacoRef.current
        if (!editor || !monaco) {
          setSql(prev => (prev ? prev + ' ' + text : text))
          return
        }
        const pos = editor.getPosition()
        if (!pos) {
          setSql(prev => (prev ? prev + ' ' + text : text))
          return
        }
        const range = new monaco.Range(pos.lineNumber, pos.column, pos.lineNumber, pos.column)
        editor.executeEdits('insert-sql', [{ range, text, forceMoveMarkers: true }])
        editor.focus()
      } catch {
        setSql(prev => (prev ? prev + ' ' + text : text))
      }
    }
    window.addEventListener('insert-sql', handler as EventListener)
    return () => window.removeEventListener('insert-sql', handler as EventListener)
  }, [])

  const handleDownloadSQL = useCallback(() => {
    const blob = new Blob([sql], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `query_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.sql`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    // SQL query downloaded successfully
  }, [sql])

  // Listen for SQL file uploads from FileUpload component
  useEffect(() => {
    const handleSqlFileLoaded = (event: CustomEvent) => {
      setSql(event.detail)
    }

    window.addEventListener('sql-file-loaded', handleSqlFileLoaded as EventListener)
    
    return () => {
      window.removeEventListener('sql-file-loaded', handleSqlFileLoaded as EventListener)
    }
  }, [])

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault()
      handleExecute(false)
    }
  }, [handleExecute])

  return (
    <div className="h-full flex flex-col glass-panel">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 dark:border-gray-700/30">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
          <span className="inline-block w-10 text-right">SQL</span>
          <span> Editor</span>
        </h2>
        <div className="flex items-center space-x-2">
          {/* Clear editor */}
          <button
            onClick={() => { if (window.confirm('Clear the SQL editor?')) { setSql('') } }}
            className="p-1.5 rounded-xl hover:bg-white/50 dark:hover:bg-gray-700/50 transition-colors"
            title="Clear editor"
          >
            <Trash2 className="w-4 h-4 text-gray-600 dark:text-gray-400" />
          </button>

          {/* Download SQL button */}
          <button
            onClick={handleDownloadSQL}
            className="p-1.5 rounded-xl hover:bg-white/50 dark:hover:bg-gray-700/50 transition-colors"
            title="Download SQL query"
          >
            <Download className="w-4 h-4 text-gray-600 dark:text-gray-400" />
          </button>

          {/* Divider */}
          <div className="h-6 w-px bg-gray-300/50 dark:bg-gray-600/50" />

          {/* Preview button - always separate */}
          <button
            onClick={() => handleExecute(true)}
            disabled={!currentFile || isExecuting || queryMutation.isPending}
            className={`
              flex items-center space-x-2 px-3 py-1.5 rounded-xl text-sm transition-all
              ${!currentFile || isExecuting || queryMutation.isPending
                ? 'bg-gray-200/50 text-gray-400 cursor-not-allowed dark:bg-gray-700/50'
                : 'bg-white/50 text-gray-700 hover:bg-white hover:shadow-sm dark:bg-gray-700/50 dark:text-gray-300 dark:hover:bg-gray-700'
              }
            `}
          >
            <Zap className="w-4 h-4" />
            <span>Preview</span>
          </button>

          {/* Run + Stop button group */}
          <div className="flex">
            {/* Run button */}
            <button
              onClick={() => handleExecute(false)}
              disabled={!currentFile || isExecuting || queryMutation.isPending}
              className={`
                flex items-center space-x-2 px-4 py-1.5 text-sm font-medium transition-all shadow-sm
                ${isExecuting
                  ? 'bg-primary-600 text-white rounded-l-xl'
                  : 'bg-primary-600 hover:bg-primary-700 text-white hover:shadow-md rounded-xl'
                }
                ${!currentFile || isExecuting || queryMutation.isPending ? 'opacity-50 cursor-not-allowed' : ''}
              `}
            >
              {isExecuting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Running</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  <span>Run</span>
                </>
              )}
            </button>

            {/* Stop button - attached to Run button when executing */}
            {isExecuting && (
              <button
                onClick={handleStop}
                className="px-2.5 py-1.5 bg-accent-red text-white hover:opacity-90 rounded-r-xl border-l border-red-800 transition-all animate-slide-in shadow-sm"
                title="Stop execution"
              >
                <Square className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>
      
      <div className="flex-1" style={{ minHeight: 0 }}>
        <Editor
          height="100%"
          language="sql"
          value={sql}
          onChange={(value) => setSql(value || '')}
          theme="vs-dark"
          loading={<div className="flex items-center justify-center h-full text-gray-500">Loading editor...</div>}
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            lineNumbers: 'on',
            renderWhitespace: 'selection',
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 2,
            wordWrap: 'on',
            bracketPairColorization: { enabled: true },
            readOnly: false,
            domReadOnly: false,
            readOnlyMessage: { value: 'Cannot edit in read-only mode' }
          }}
          onMount={(editor, monaco) => {
            // Ensure editor is not read-only
            editor.updateOptions({ readOnly: false })
            editorRef.current = editor
            monacoRef.current = monaco
            
            // Add keyboard shortcut
            editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => handleExecute(false))
            
            // Focus the editor
            setTimeout(() => {
              editor.focus()
            }, 100)
          }}
        />
      </div>
      
      <div className="px-4 py-2 border-t border-white/10 dark:border-gray-700/30 text-xs text-gray-500 dark:text-gray-400">
        Press <kbd className="px-1.5 py-0.5 rounded bg-white/50 dark:bg-gray-700/50 font-mono">{getModifierKey()}+Enter</kbd> to run
      </div>
    </div>
  )
}
