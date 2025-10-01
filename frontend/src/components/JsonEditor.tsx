import { useState, useCallback, useRef } from 'react'
import Editor from '@monaco-editor/react'
import { Play, Square, Zap, Loader2, Download, Trash2 } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useSessionStore } from '@/stores/sessionStore'
import { useJsonStore } from '@/stores/jsonStore'
import { useSettingsStore } from '@/stores/settingsStore'

// Helper to get the correct modifier key based on platform
const getModifierKey = () => {
  // Check multiple ways to detect Mac
  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0 ||
                navigator.userAgent.toUpperCase().indexOf('MAC') >= 0 ||
                (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1) // M1 iPads
  
  return isMac ? 'Cmd' : 'Ctrl'
}

export function JsonEditor() {
  const { sessionId } = useSessionStore()
  const { previewRowCount } = useSettingsStore()
  const { setConversionResult, setIsConverting, isConverting, abortController, setAbortController, jsonContent, setJsonContent, actualJsonContent, setActualJsonContent } = useJsonStore()
  const editorRef = useRef<any>(null)
  const monacoRef = useRef<any>(null)

  const convertMutation = useMutation({
    mutationFn: async (isPreview: boolean = false) => {
      if (!sessionId) throw new Error('No session')
      
      // Create new abort controller for this conversion
      const controller = new AbortController()
      setAbortController(controller)
      setIsConverting(true)
      
      // Use actualJsonContent for conversion (full content), not the preview
      let contentToConvert = actualJsonContent || jsonContent
      
      // Validate JSON
      let parsedJson
      try {
        parsedJson = JSON.parse(contentToConvert)
      } catch (e) {
        throw new Error('Invalid JSON format')
      }
      
      // For preview, randomly sample rows
      if (isPreview && Array.isArray(parsedJson)) {
        const totalRows = parsedJson.length
        if (totalRows > previewRowCount) {
          // Create random indices
          const indices = new Set<number>()
          while (indices.size < previewRowCount) {
            indices.add(Math.floor(Math.random() * totalRows))
          }
          // Sample the data
          const sampledData = Array.from(indices).sort((a, b) => a - b).map(i => parsedJson[i])
          contentToConvert = JSON.stringify(sampledData)
        }
      }
      
      // Pass abort signal to API call
      return api.convertJson(sessionId, contentToConvert, {
        expand_arrays: false,  // Don't expand arrays for large files
        max_depth: 2,  // Even lower depth for faster processing
        auto_safe: true,
        include_summary: false,  // Skip summary for faster processing
      }, controller.signal)
    },
    onSuccess: (data) => {
      setConversionResult(data)
    },
    onError: (error: any) => {
      // Ignore abort errors
      if (error.name !== 'AbortError') {
        console.error('Conversion error:', error.message)
      }
    },
    onSettled: () => {
      setIsConverting(false)
      setAbortController(null)
    },
  })

  const handleConvert = useCallback(() => {
    if (isConverting || convertMutation.isPending) {
      console.warn('Conversion already in progress, please wait...')
      return
    }
    convertMutation.mutate(false)
  }, [convertMutation, isConverting])

  const handlePreview = useCallback(() => {
    if (isConverting || convertMutation.isPending) {
      console.warn('Conversion already in progress, please wait...')
      return
    }
    convertMutation.mutate(true)
  }, [convertMutation, isConverting])

  const handleStop = useCallback(() => {
    if (abortController) {
      abortController.abort()
      setIsConverting(false)
      setAbortController(null)
    }
  }, [abortController, setIsConverting, setAbortController])

  const handleDownloadJSON = useCallback(() => {
    const blob = new Blob([jsonContent], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `data_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }, [jsonContent])

  const formatJson = useCallback(() => {
    if (!editorRef.current) return
    editorRef.current.getAction('editor.action.formatDocument')?.run()
  }, [])

  return (
    <div className="h-full flex flex-col glass-panel">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 dark:border-gray-700/30">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
          <span className="inline-block w-10 text-right">JSON</span>
          <span> Editor</span>
        </h2>
        <div className="flex items-center space-x-2">
          {/* Clear editor */}
          <button
            onClick={() => {
              if (window.confirm('Clear the JSON editor?')) {
                const defaultContent = `{
  "example": "Paste your JSON here",
  "array": [1, 2, 3],
  "nested": {
    "key": "value"
  }
}`
                setJsonContent(defaultContent)
                setActualJsonContent(defaultContent)
                setConversionResult(null)
              }
            }}
            className="p-1.5 rounded-xl hover:bg-white/50 dark:hover:bg-gray-700/50 transition-colors"
            title="Clear editor"
          >
            <Trash2 className="w-4 h-4 text-gray-600 dark:text-gray-400" />
          </button>

          {/* Download JSON button */}
          <button
            onClick={handleDownloadJSON}
            className="p-1.5 rounded-xl hover:bg-white/50 dark:hover:bg-gray-700/50 transition-colors"
            title="Download JSON"
          >
            <Download className="w-4 h-4 text-gray-600 dark:text-gray-400" />
          </button>

          {/* Divider */}
          <div className="h-6 w-px bg-gray-300/50 dark:bg-gray-600/50" />

          {/* Preview button - always separate */}
          <button
            onClick={() => handlePreview()}
            disabled={!jsonContent || isConverting}
            className={`
              flex items-center space-x-2 px-3 py-1.5 rounded-xl text-sm transition-all
              ${!jsonContent || isConverting
                ? 'bg-gray-200/50 text-gray-400 cursor-not-allowed dark:bg-gray-700/50'
                : 'bg-white/50 text-gray-700 hover:bg-white hover:shadow-sm dark:bg-gray-700/50 dark:text-gray-300 dark:hover:bg-gray-700'
              }
            `}
          >
            <Zap className="w-4 h-4" />
            <span>Preview</span>
          </button>

          {/* Convert + Stop button group */}
          <div className="flex">
            {/* Convert button */}
            <button
              onClick={() => handleConvert()}
              disabled={!jsonContent}
              className={`
                flex items-center space-x-2 px-4 py-1.5 text-sm font-medium transition-all shadow-sm
                ${isConverting
                  ? 'bg-primary-600 text-white rounded-l-xl'
                  : 'bg-primary-600 hover:bg-primary-700 text-white hover:shadow-md rounded-xl'
                }
                ${!jsonContent ? 'opacity-50 cursor-not-allowed' : ''}
              `}
            >
              {isConverting ? (
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

            {/* Stop button - attached to Convert button when converting */}
            {isConverting && (
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
          language="json"
          value={jsonContent}
          onChange={(value) => setJsonContent(value || '')}
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
            readOnly: jsonContent.includes('... File truncated for preview'),
            domReadOnly: jsonContent.includes('... File truncated for preview'),
            readOnlyMessage: { value: 'File too large - showing preview only' }
          }}
          onMount={(editor, monaco) => {
            // Ensure editor is not read-only
            editor.updateOptions({ readOnly: false })
            editorRef.current = editor
            monacoRef.current = monaco
            
            // Configure JSON language settings
            monaco.languages.json.jsonDefaults.setDiagnosticsOptions({
              validate: true,
              schemas: [],
              allowComments: false,
              trailingCommas: false,
            })
            
            // Add keyboard shortcut
            editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => handleConvert())
            
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