import { useState, useCallback, useEffect, useRef } from 'react'
import Editor from '@monaco-editor/react'
import { Play, Square, Zap, Loader2, Undo, Redo, Trash2, BookOpen, Save, ChevronDown, Eye, X, Eraser } from 'lucide-react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useSessionStore } from '@/stores/sessionStore'
import { useEditorStore } from '@/stores/editorStore'
import { useQueriesStore } from '@/stores/queriesStore'
import { findExactMatch } from '@/lib/sqlUtils'
import { useRecentQueries } from '@/hooks/useRecentQueries'
import * as settingsApi from '@/lib/settingsApi'

// Helper to get the correct modifier key based on platform
const getModifierKey = () => {
  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0 ||
                navigator.userAgent.toUpperCase().indexOf('MAC') >= 0 ||
                (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
  return isMac ? 'Cmd' : 'Ctrl'
}

// SQL editor is SQL-only now - no JSON detection
const detectContentType = (code: string): 'sql' | 'json' => {
  return 'sql'
}

export function CodeEditorPanel() {
  const { sessionId, currentFile, setCurrentQuery, setCurrentFile, isExecuting, setIsExecuting } = useSessionStore()
  const { code, setCode, contentType, setContentType, hasExecuted, setHasExecuted } = useEditorStore()

  const PREVIEW_ROW_LIMIT = 10 // Hardcoded preview limit for quick results
  const [showPlaceholder, setShowPlaceholder] = useState(true)
  const editorRef = useRef<any>(null)
  const monacoRef = useRef<any>(null)
  const [canUndo, setCanUndo] = useState(false)
  const [canRedo, setCanRedo] = useState(false)
  const [savedCode, setSavedCode] = useState('')
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)

  // Library/Save button state
  const [matchedQuery, setMatchedQuery] = useState<{id: number, name: string} | null>(null)
  const [showLibraryDropdown, setShowLibraryDropdown] = useState(false)
  const { recentQueries, addRecent } = useRecentQueries()

  // Fetch all saved queries for matching
  const { data: savedQueries } = useQuery({
    queryKey: ['saved-queries'],
    queryFn: () => settingsApi.getSavedQueries(),
  })

  // Check for exact match when code changes or queries load
  const checkExactMatch = useCallback(() => {
    if (!code.trim() || !savedQueries) {
      setMatchedQuery(null)
      return
    }

    const match = findExactMatch(code, savedQueries)
    setMatchedQuery(match)
  }, [code, savedQueries])

  // Run exact match check whenever code or saved queries change
  useEffect(() => {
    checkExactMatch()
  }, [checkExactMatch])

  // Force SQL-only mode
  useEffect(() => {
    setContentType('sql')
  }, [])

  // Hide placeholder when file is loaded
  useEffect(() => {
    if (currentFile) {
      setShowPlaceholder(false)
    }
  }, [currentFile])

  const queryMutation = useMutation({
    mutationKey: ['execute-query', sessionId, contentType, code.substring(0, 100)],
    mutationFn: async (isPreview: boolean = false) => {
      console.log('🔧 queryMutation.mutationFn called with isPreview:', isPreview, 'contentType:', contentType)
      if (!sessionId) throw new Error('No session')

      // Route to correct endpoint based on content type
      if (contentType === 'json') {
        let jsonToConvert = code
        let originalTotal = 0

        console.log('📦 JSON mode, code length:', code.length, 'isPreview:', isPreview)

        // For preview, sample the JSON data
        if (isPreview) {
          console.log('🔍 Entering preview sampling block...')
          console.log('⏱️ Starting JSON.parse on', code.length, 'characters...')
          try {
            const parsedJson = JSON.parse(code)
            console.log('✅ JSON parsed successfully. Type:', typeof parsedJson, 'isArray:', Array.isArray(parsedJson))
            if (Array.isArray(parsedJson)) {
              const totalRows = parsedJson.length
              originalTotal = totalRows
              console.log('🔍 JSON Preview: Original rows:', totalRows, 'Limit:', PREVIEW_ROW_LIMIT)

              if (totalRows > PREVIEW_ROW_LIMIT) {
                // Random sample
                console.log('🎲 Creating random sample...')
                const indices = new Set<number>()
                while (indices.size < PREVIEW_ROW_LIMIT) {
                  indices.add(Math.floor(Math.random() * totalRows))
                }
                const sampledData = Array.from(indices).sort((a, b) => a - b).map(i => parsedJson[i])
                jsonToConvert = JSON.stringify(sampledData)
                console.log('✂️ Sampled to', sampledData.length, 'rows')
              } else {
                console.log('⚠️ Total rows', totalRows, '<= limit', PREVIEW_ROW_LIMIT, '- using all data')
              }
            } else {
              console.log('⚠️ JSON is not an array, skipping sampling')
            }
          } catch (e) {
            console.error('❌ Failed to parse JSON for sampling:', e)
          }
        }

        const result = await api.convertJson(sessionId, jsonToConvert, {
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
          row_count: originalTotal > 0 ? originalTotal : result.total_rows,
          column_count: result.columns?.length || 0,
          columns: result.columns || [],
          execution_time_ms: 0,
          preview: result.preview || [],
          has_more: result.total_rows > (result.preview?.length || 0),
          is_preview_only: isPreview,  // Flag to indicate if this is preview-only (not downloadable)
          original_total_rows: originalTotal > 0 ? originalTotal : result.total_rows,
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

      // Check for exact match after successful execution
      checkExactMatch()

      // If matched and in library, add to recents
      if (matchedQuery && savedQueries) {
        const fullQuery = savedQueries.find(q => q.id === matchedQuery.id)
        if (fullQuery) {
          console.log('📝 Adding to recent queries:', fullQuery.name)
          addRecent({
            id: fullQuery.id,
            name: fullQuery.name,
            query: fullQuery.query
          })
        }
      } else {
        console.log('ℹ️ Query not added to recents (not in library or no match)')
      }

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

    },
    onError: (error: any) => {
      console.error('Query failed:', error.response?.data?.detail || error)
    },
    onSettled: () => {
      setIsExecuting(false)
    },
  })

  const handleExecute = useCallback((isPreview: boolean = false) => {
    console.log('🎯 handleExecute called with isPreview:', isPreview, 'contentType:', contentType, 'isPending:', queryMutation.isPending)
    // SQL workspace requires file upload first
    if (!currentFile) {
      console.error('Please load a file first')
      return
    }
    if (queryMutation.isPending) {
      console.warn('⚠️ Already executing, IGNORING this call')
      return
    }
    console.log('✅ Calling queryMutation.mutate...')
    setCurrentQuery(null)
    queryMutation.mutate(isPreview)
  }, [currentFile, queryMutation, setCurrentQuery])

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

  const updateUndoRedoState = useCallback(() => {
    if (editorRef.current) {
      const model = editorRef.current.getModel()
      if (model) {
        setCanUndo(model.canUndo())
        setCanRedo(model.canRedo())
      }
    }
  }, [])

  const handleUndo = useCallback(() => {
    if (editorRef.current && canUndo) {
      editorRef.current.trigger('keyboard', 'undo', null)
      // Update state after undo
      setTimeout(updateUndoRedoState, 10)
    }
  }, [canUndo, updateUndoRedoState])

  const handleRedo = useCallback(() => {
    if (editorRef.current && canRedo) {
      editorRef.current.trigger('keyboard', 'redo', null)
      // Update state after redo
      setTimeout(updateUndoRedoState, 10)
    }
  }, [canRedo, updateUndoRedoState])

  const handleRevert = useCallback(() => {
    if (window.confirm('Are you sure you want to revert to the last saved version? All unsaved changes will be lost.')) {
      setCode(savedCode)
      setHasUnsavedChanges(false)
    }
  }, [savedCode, setCode])

  const handleSave = useCallback(() => {
    // Save current code
    setSavedCode(code)
    setHasUnsavedChanges(false)
    console.log('Code saved')
    // TODO: Implement actual file save to backend
  }, [code])

  const handleClear = useCallback(() => {
    if (window.confirm('Clear the editor? This will remove all code.')) {
      setCode('')
      setSavedCode('')
      setHasUnsavedChanges(false)
      setHasExecuted(false)
    }
  }, [setCode, setHasExecuted])

  const handleSaveToLibrary = useCallback(() => {
    // Open Library modal with editor pre-filled
    window.dispatchEvent(new CustomEvent('open-library-with-code', {
      detail: {
        name: `query_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}`,
        content: code
      }
    }))
  }, [code])

  const handleOpenLibrary = useCallback(() => {
    // Open full Library modal to list view
    window.dispatchEvent(new CustomEvent('open-library'))
  }, [])

  const handleLoadRecentQuery = useCallback((query: {id: number, name: string, query: string}) => {
    console.log('📖 Loading recent query from dropdown:', query.name)
    setCode(query.query)
    setShowLibraryDropdown(false)
    // Will trigger match check via useEffect
  }, [setCode])

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

  const editorLanguage = 'sql'
  const canExecute = !!currentFile

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center px-2 py-2 border-b-2 border-gray-600 dark:border-gray-400">
        {/* Grouped pills design - tighter spacing, smaller icons */}
        <div className="flex items-center gap-3">
          {/* Group 1: Undo + Redo (always visible, grayed when disabled) */}
          <div className="flex items-center px-1.5 py-0.5 rounded-md bg-gray-100/50 dark:bg-gray-800/50">
            <button
              onClick={handleUndo}
              disabled={!canUndo}
              className={`p-1 rounded ${
                canUndo
                  ? 'hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
                  : 'opacity-40 cursor-not-allowed text-gray-400 dark:text-gray-600'
              }`}
              title={canUndo ? "Undo (Cmd+Z)" : "Nothing to undo"}
            >
              <Undo className="w-4 h-4" />
            </button>

            <button
              onClick={handleRedo}
              disabled={!canRedo}
              className={`p-1 rounded ${
                canRedo
                  ? 'hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
                  : 'opacity-40 cursor-not-allowed text-gray-400 dark:text-gray-600'
              }`}
              title={canRedo ? "Redo (Cmd+Shift+Z)" : "Nothing to redo"}
            >
              <Redo className="w-4 h-4" />
            </button>
          </div>

          {/* Library/Save Button - Dynamic based on exact match */}
          <div className="relative">
            {!code.trim() || matchedQuery ? (
              // Empty editor OR exact match found → Show Library dropdown
              <div className="relative">
                <button
                  onClick={() => setShowLibraryDropdown(!showLibraryDropdown)}
                  className="flex items-center space-x-1 px-2 py-1 rounded-md bg-gray-100/50 dark:bg-gray-800/50 hover:bg-gray-200 dark:hover:bg-gray-700"
                  title={matchedQuery ? `Matched: ${matchedQuery.name}` : 'Browse Library'}
                >
                  <BookOpen className="w-4 h-4 text-gray-700 dark:text-gray-300" />
                  <span className="text-xs text-gray-700 dark:text-gray-300 max-w-[120px] truncate">
                    {matchedQuery ? matchedQuery.name : 'Library'}
                  </span>
                  <ChevronDown className="w-3 h-3 text-gray-700 dark:text-gray-300" />
                </button>

                {/* Dropdown */}
                {showLibraryDropdown && (
                  <>
                    {/* Backdrop to close dropdown */}
                    <div
                      className="fixed inset-0 z-10"
                      onClick={() => setShowLibraryDropdown(false)}
                    />
                    <div className="absolute top-full left-0 mt-1 w-64 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-20">
                      {/* Browse Full Library */}
                      <button
                        onClick={() => {
                          handleOpenLibrary()
                          setShowLibraryDropdown(false)
                        }}
                        className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-800 flex items-center space-x-2 border-b border-gray-200 dark:border-gray-700"
                      >
                        <BookOpen className="w-4 h-4" />
                        <span>Browse Full Library</span>
                      </button>

                      {/* Recent Queries */}
                      {recentQueries.length > 0 && (
                        <div className="py-1">
                          <div className="px-4 py-1 text-xs text-gray-500 dark:text-gray-400">
                            Recent:
                          </div>
                          {recentQueries.map((query) => (
                            <button
                              key={query.id}
                              onClick={() => handleLoadRecentQuery(query)}
                              className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-800"
                            >
                              <div className="font-medium text-gray-900 dark:text-gray-100 truncate">
                                {query.name}
                              </div>
                              <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                                {query.query.substring(0, 50)}...
                              </div>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            ) : (
              // Has code but NO exact match → Show Save button
              <button
                onClick={handleSaveToLibrary}
                className="flex items-center space-x-1 px-2 py-1 rounded-md bg-gray-100/50 dark:bg-gray-800/50 hover:bg-gray-200 dark:hover:bg-gray-700"
                title="Save to Library"
              >
                <Save className="w-4 h-4 text-gray-700 dark:text-gray-300" />
                <span className="text-xs text-gray-700 dark:text-gray-300">
                  Save to Library
                </span>
              </button>
            )}
          </div>

          {/* Group 2: Revert (X) + Save */}
          <div className="flex items-center px-1.5 py-0.5 rounded-md bg-gray-100/50 dark:bg-gray-800/50">
            {/* Revert button (X) - only enabled if there are unsaved changes */}
            <button
              onClick={handleRevert}
              disabled={!hasUnsavedChanges}
              className={`p-1 rounded ${
                hasUnsavedChanges
                  ? 'hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
                  : 'opacity-40 cursor-not-allowed text-gray-400 dark:text-gray-600'
              }`}
              title={hasUnsavedChanges ? "Revert to last save" : "No unsaved changes"}
            >
              <X className="w-4 h-4" />
            </button>

            {/* Save button - only enabled if there are unsaved changes */}
            <button
              onClick={handleSave}
              disabled={!hasUnsavedChanges}
              className={`p-1 rounded ${
                hasUnsavedChanges
                  ? 'hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
                  : 'opacity-40 cursor-not-allowed text-gray-400 dark:text-gray-600'
              }`}
              title={hasUnsavedChanges ? "Save changes" : "No changes to save"}
            >
              <Save className="w-4 h-4" />
            </button>
          </div>

          {/* Group 3: Clear */}
          <div className="flex items-center px-1.5 py-0.5 rounded-md bg-gray-100/50 dark:bg-gray-800/50">
            {/* Clear button - disabled if there are unsaved changes */}
            <button
              onClick={handleClear}
              disabled={!code.trim() || hasUnsavedChanges}
              className={`p-1 rounded ${
                !code.trim() || hasUnsavedChanges
                  ? 'opacity-40 cursor-not-allowed text-gray-400 dark:text-gray-600'
                  : 'hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
              }`}
              title={
                hasUnsavedChanges
                  ? 'Unavailable until changes are saved or reverted'
                  : !code.trim()
                    ? 'No code to clear'
                    : 'Clear editor'
              }
            >
              <Eraser className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 relative" style={{ minHeight: 0 }}>
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
            unusualLineTerminators: 'auto',  // Automatically remove unusual line terminators
            unicodeHighlight: {
              ambiguousCharacters: false,  // Disable ambiguous character warnings
              invisibleCharacters: false,  // Disable invisible character warnings
            }
          }}
          onMount={(editor, monaco) => {
            editor.updateOptions({
              readOnly: false,
              unusualLineTerminators: 'auto',  // Automatically remove unusual line terminators
              unicodeHighlight: {
                ambiguousCharacters: false,  // Disable ambiguous character warnings
                invisibleCharacters: false,  // Disable invisible character warnings
              }
            })
            editorRef.current = editor
            monacoRef.current = monaco

            // Track undo/redo state changes
            const model = editor.getModel()
            if (model) {
              model.onDidChangeContent(() => {
                updateUndoRedoState()
                // Check if content has changed from saved version
                const currentCode = model.getValue()
                setHasUnsavedChanges(currentCode !== savedCode)
              })
            }

            // Initial undo/redo state
            updateUndoRedoState()

            editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => handleExecute(false))

            setTimeout(() => {
              editor.focus()
            }, 100)
          }}
        />
      </div>
    </div>
  )
}
