import { useState, useCallback, useEffect, useRef } from 'react'
import Editor from '@monaco-editor/react'
import { Play, Square, Zap, Loader2, Download, Trash2, Upload } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useSessionStore } from '@/stores/sessionStore'
import { useEditorStore } from '@/stores/editorStore'
import { useSettingsStore } from '@/stores/settingsStore'
import { useHistoryStore } from '@/stores/historyStore'
import { useQueriesStore } from '@/stores/queriesStore'

// Helper to get the correct modifier key based on platform
const getModifierKey = () => {
  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0 ||
                navigator.userAgent.toUpperCase().indexOf('MAC') >= 0 ||
                (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
  return isMac ? 'Cmd' : 'Ctrl'
}

// Detect content type from code
const detectContentType = (code: string): 'sql' | 'json' => {
  const trimmed = code.trim()
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) return 'json'
  if (/^(SELECT|WITH|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)/i.test(trimmed)) return 'sql'
  // Default to SQL for empty or ambiguous content
  return 'sql'
}

export function CodeEditor() {
  const { sessionId, currentFile, setCurrentQuery, setCurrentFile, isExecuting, setIsExecuting } = useSessionStore()
  const { code, setCode, contentType, setContentType, hasExecuted, setHasExecuted } = useEditorStore()
  const { addToHistory } = useHistoryStore()

  const PREVIEW_ROW_LIMIT = 10 // Hardcoded preview limit for quick results
  const [showPlaceholder, setShowPlaceholder] = useState(true)
  const editorRef = useRef<any>(null)
  const monacoRef = useRef<any>(null)

  // Auto-detect content type when code changes
  useEffect(() => {
    if (code.trim()) {
      setShowPlaceholder(false)
      const detected = detectContentType(code)
      setContentType(detected)
    } else {
      setShowPlaceholder(true)
    }
  }, [code, setContentType])

  // Hide placeholder when file is loaded
  useEffect(() => {
    if (currentFile) {
      setShowPlaceholder(false)
    }
  }, [currentFile])

  const queryMutation = useMutation({
    mutationFn: async (isPreview: boolean = false) => {
      if (!sessionId) throw new Error('No session')

      // Route to correct endpoint based on content type
      if (contentType === 'json') {
        const result = await api.convertJson(sessionId, code, {
          expand_arrays: true,
          include_summary: false,  // Disable summary to get actual data in preview
          preview_only: isPreview,  // Only analyze structure for preview, don't do full conversion
          limit: isPreview ? PREVIEW_ROW_LIMIT : undefined,  // Apply preview row limit (10 rows)
        })

        // Log the result for debugging
        console.log('JSON conversion result:', result)

        // Transform JSON conversion result to match QueryResponse format
        return {
          query_id: `json_${Date.now()}`,
          row_count: result.total_rows,
          column_count: result.columns?.length || 0,
          columns: result.columns || [],
          execution_time_ms: 0,
          preview: result.preview || [],
          has_more: result.total_rows > (result.preview?.length || 0),
          is_preview_only: isPreview,  // Flag to indicate if this is preview-only (not downloadable)
        }
      } else {
        const limit = isPreview ? PREVIEW_ROW_LIMIT : null
        const result = await api.executeQuery(sessionId, code, {
          limit,
          is_preview: isPreview
        })
        // Mark SQL previews as non-downloadable
        if (isPreview) {
          return { ...result, is_preview_only: true }
        }
        return result
      }
    },
    onMutate: () => {
      setIsExecuting(true)
    },
    onSuccess: (data) => {
      setCurrentQuery(data)
      setHasExecuted(true)

      // If JSON conversion, update currentFile with column info for sidebar
      if (contentType === 'json' && data.columns && data.columns.length > 0) {
        setCurrentFile({
          filename: 'json_data.json',
          size_mb: 0,
          row_count: data.row_count,
          column_count: data.column_count,
          columns: data.columns.map((col: string) => ({
            original_name: col,
            clean_name: col,
            dtype: 'string',
            non_null_count: 0,
            null_count: 0
          }))
        })
      }

      // Auto-save to history
      addToHistory({
        query: code,
        type: contentType,
        executionTime: data.execution_time_ms,
        rowCount: data.row_count,
      })
    },
    onError: (error: any) => {
      console.error('Query failed:', error.response?.data?.detail || error)
    },
    onSettled: () => {
      setIsExecuting(false)
    },
  })

  const handleExecute = useCallback((isPreview: boolean = false) => {
    if (contentType === 'sql' && !currentFile) {
      console.error('Please load a file first')
      return
    }
    if (queryMutation.isPending) {
      console.warn('Already executing, please wait...')
      return
    }
    setCurrentQuery(null)
    queryMutation.mutate(isPreview)
  }, [contentType, currentFile, queryMutation, setCurrentQuery])

  const handleStop = useCallback(() => {
    console.log('Query cancellation not yet implemented')
  }, [])

  // Insert column names at cursor
  useEffect(() => {
    const handler = (event: CustomEvent<string>) => {
      const text = event.detail
      try {
        const editor = editorRef.current
        const monaco = monacoRef.current
        if (!editor || !monaco) {
          setCode(prev => (prev ? prev + ' ' + text : text))
          return
        }
        const pos = editor.getPosition()
        if (!pos) {
          setCode(prev => (prev ? prev + ' ' + text : text))
          return
        }
        const range = new monaco.Range(pos.lineNumber, pos.column, pos.lineNumber, pos.column)
        editor.executeEdits('insert-sql', [{ range, text, forceMoveMarkers: true }])
        editor.focus()
      } catch {
        setCode(prev => (prev ? prev + ' ' + text : text))
      }
    }
    window.addEventListener('insert-sql', handler as EventListener)
    return () => window.removeEventListener('insert-sql', handler as EventListener)
  }, [])

  const handleUploadSQL = useCallback(() => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.sql'
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (!file) return

      const reader = new FileReader()
      reader.onload = (e) => {
        const content = e.target?.result as string
        setCode(content)
        setContentType('sql')
        setHasExecuted(false)
      }
      reader.readAsText(file)
    }
    input.click()
  }, [setContentType, setHasExecuted])

  const handleDownloadCode = useCallback(() => {
    const fileType = contentType === 'json' ? 'JSON' : 'SQL'
    const extension = contentType === 'json' ? 'json' : 'sql'
    const mimeType = contentType === 'json' ? 'application/json' : 'text/plain'

    // Show prompt for both SQL and JSON
    const choice = prompt(
      `Save ${fileType} file:\n\n1 - Download to computer\n2 - Save to in-app library\n3 - Both\n\nEnter 1, 2, or 3:`
    )

    if (!choice) return

    const addQuery = useQueriesStore.getState().addQuery

    switch (choice.trim()) {
      case '1':
        // Download to computer
        const blob = new Blob([code], { type: mimeType })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${fileType.toLowerCase()}_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.${extension}`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
        break

      case '2':
        // Save to in-app library
        const name = prompt(`${fileType} file name:`)
        if (name?.trim()) {
          addQuery(name.trim(), code, contentType, null)
        }
        break

      case '3':
        // Both
        const blob3 = new Blob([code], { type: mimeType })
        const url3 = URL.createObjectURL(blob3)
        const a3 = document.createElement('a')
        a3.href = url3
        a3.download = `${fileType.toLowerCase()}_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.${extension}`
        document.body.appendChild(a3)
        a3.click()
        document.body.removeChild(a3)
        URL.revokeObjectURL(url3)

        const name3 = prompt(`${fileType} file name for in-app library:`)
        if (name3?.trim()) {
          addQuery(name3.trim(), code, contentType, null)
        }
        break

      default:
        alert('Invalid choice. Please enter 1, 2, or 3.')
    }
  }, [code, contentType])

  // Listen for file uploads (for legacy JSON upload from FileUpload component)
  useEffect(() => {
    const handleCodeFileLoaded = (event: CustomEvent) => {
      const { content, type } = event.detail
      console.log('CodeEditor received code-file-loaded event:', { type, contentLength: content.length })
      setCode(content)
      setContentType(type)
      setHasExecuted(false)
    }

    const handleClearEditor = () => {
      setCode('')
      setHasExecuted(false)
    }

    window.addEventListener('code-file-loaded', handleCodeFileLoaded as EventListener)
    window.addEventListener('clear-code-editor', handleClearEditor as EventListener)

    return () => {
      window.removeEventListener('code-file-loaded', handleCodeFileLoaded as EventListener)
      window.removeEventListener('clear-code-editor', handleClearEditor as EventListener)
    }
  }, [setCode, setContentType, setHasExecuted])

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault()
      handleExecute(false)
    }
  }, [handleExecute])

  const editorLanguage = contentType === 'json' ? 'json' : 'sql'
  const canExecute = contentType === 'json' ? true : !!currentFile

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-800">
        <h2 className="text-sm font-medium">Code Editor</h2>
        <div className="flex items-center space-x-2">
          {/* Upload SQL button */}
          <button
            onClick={handleUploadSQL}
            className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
            title="Upload SQL file"
          >
            <Upload className="w-4 h-4 text-gray-600 dark:text-gray-400" />
          </button>

          {/* Download code button */}
          <button
            onClick={handleDownloadCode}
            className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
            title={`Download ${contentType === 'json' ? 'JSON' : 'SQL'}`}
          >
            <Download className="w-4 h-4 text-gray-600 dark:text-gray-400" />
          </button>

          {/* Divider */}
          <div className="h-6 w-px bg-gray-200 dark:bg-gray-700" />

          {/* Preview button */}
          <button
            onClick={() => handleExecute(true)}
            disabled={!canExecute || isExecuting || queryMutation.isPending}
            className={`
              flex items-center space-x-2 px-3 py-1.5 rounded-md text-sm
              ${!canExecute || isExecuting || queryMutation.isPending
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed dark:bg-gray-800'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
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
              disabled={!canExecute || isExecuting || queryMutation.isPending}
              className={`
                flex items-center space-x-2 px-3 py-1.5 text-sm transition-all
                ${isExecuting
                  ? 'bg-primary-600 text-white rounded-l-md'
                  : 'bg-primary-600 text-white hover:bg-primary-700 rounded-md'
                }
                ${!canExecute || isExecuting || queryMutation.isPending ? 'opacity-50 cursor-not-allowed' : ''}
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

            {/* Stop button */}
            {isExecuting && (
              <button
                onClick={handleStop}
                className="px-2.5 py-1.5 bg-red-600 text-white hover:bg-red-700 rounded-r-md border-l border-red-700 transition-all"
                title="Stop execution"
              >
                <Square className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Divider */}
          <div className="h-6 w-px bg-gray-200 dark:bg-gray-700" />

          {/* Trash button */}
          <button
            onClick={() => { if (window.confirm('Clear the editor?')) { setCode(''); setHasExecuted(false) } }}
            className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
            title="Clear editor"
          >
            <Trash2 className="w-4 h-4 text-gray-600 dark:text-gray-400" />
          </button>
        </div>
      </div>

      <div className="flex-1 relative" style={{ minHeight: 0 }}>
        {/* Placeholder hint - shows when editor is empty */}
        {showPlaceholder && (
          <div className="absolute inset-0 pointer-events-none flex items-start pt-4 pl-16 z-10">
            <span className="text-gray-500 dark:text-gray-600 text-sm font-mono">
              // Upload a file or paste your SQL query / JSON data here to get started...
            </span>
          </div>
        )}

        <Editor
          height="100%"
          language={editorLanguage}
          value={code}
          onChange={(value) => setCode(value || '')}
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
          }}
          onMount={(editor, monaco) => {
            editor.updateOptions({ readOnly: false })
            editorRef.current = editor
            monacoRef.current = monaco

            editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => handleExecute(false))

            setTimeout(() => {
              editor.focus()
            }, 100)
          }}
        />
      </div>

      <div className="px-4 py-2 border-t border-gray-200 dark:border-gray-800 text-xs text-gray-500">
        {code.trim() ? (
          <>Press {getModifierKey()}+Enter to run • {contentType === 'json' ? 'JSON Mode' : 'SQL Mode'}</>
        ) : (
          <>Press {getModifierKey()}+Enter to run</>
        )}
      </div>
    </div>
  )
}
