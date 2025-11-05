/**
 * MonacoEditor - VS Code's Monaco editor for Code Tab
 * Phase 2: Read-only file viewing
 * Phase 3+: Full editing with diff preview
 */

import { useRef, useEffect } from 'react'
import Editor, { OnMount } from '@monaco-editor/react'
import { editor } from 'monaco-editor'

interface MonacoEditorProps {
  value: string
  language?: string
  readOnly?: boolean
  onValueChange?: (value: string) => void
  theme?: 'vs-dark' | 'light'
}

export function MonacoEditor({
  value,
  language = 'typescript',
  readOnly = true,
  onValueChange,
  theme = 'vs-dark'
}: MonacoEditorProps) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null)

  const handleEditorDidMount: OnMount = (editor, monaco) => {
    editorRef.current = editor

    // Configure Monaco (Continue's patterns)
    monaco.editor.defineTheme('elohim-dark', {
      base: 'vs-dark',
      inherit: true,
      rules: [],
      colors: {
        'editor.background': '#111827', // gray-900
      },
    })

    monaco.editor.defineTheme('elohim-light', {
      base: 'vs',
      inherit: true,
      rules: [],
      colors: {
        'editor.background': '#f9fafb', // gray-50
      },
    })

    // Set theme
    monaco.editor.setTheme(theme === 'vs-dark' ? 'elohim-dark' : 'elohim-light')

    // Focus editor
    editor.focus()
  }

  const handleEditorChange = (value: string | undefined) => {
    if (value !== undefined && onValueChange && !readOnly) {
      onValueChange(value)
    }
  }

  // Update theme when it changes
  useEffect(() => {
    if (editorRef.current) {
      const monaco = (window as any).monaco
      if (monaco) {
        monaco.editor.setTheme(theme === 'vs-dark' ? 'elohim-dark' : 'elohim-light')
      }
    }
  }, [theme])

  return (
    <Editor
      height="100%"
      language={language}
      value={value}
      theme={theme === 'vs-dark' ? 'elohim-dark' : 'elohim-light'}
      onMount={handleEditorDidMount}
      onChange={handleEditorChange}
      options={{
        readOnly,
        minimap: { enabled: true },
        fontSize: 14,
        lineNumbers: 'on',
        renderWhitespace: 'selection',
        scrollBeyondLastLine: false,
        automaticLayout: true,
        wordWrap: 'off',
        tabSize: 2,
        insertSpaces: true,
        // Continue's patterns for better UX
        suggest: {
          preview: true,
        },
        quickSuggestions: !readOnly,
        parameterHints: { enabled: !readOnly },
        folding: true,
        foldingStrategy: 'indentation',
        showFoldingControls: 'always',
        matchBrackets: 'always',
        formatOnPaste: !readOnly,
        formatOnType: !readOnly,
      }}
    />
  )
}
