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
  const observerRef = useRef<MutationObserver | null>(null)
  const intervalRef = useRef<number | null>(null)

  const handleEditorDidMount: OnMount = (editor, monaco) => {
    editorRef.current = editor

    // Function to add name and id attributes to Monaco textareas
    const addNameToTextareas = (node: HTMLElement) => {
      const textareas = node.querySelectorAll('textarea.inputarea') as NodeListOf<HTMLTextAreaElement>
      textareas.forEach((ta, index) => {
        if (!ta.getAttribute('name')) {
          ta.setAttribute('name', 'monaco_editor_content')
        }
        if (!ta.getAttribute('id')) {
          ta.setAttribute('id', `monaco_editor_textarea_${index}`)
        }
      })
    }

    // Ensure internal textarea has a name attribute for accessibility/autofill tools
    const domNode = editor.getDomNode()
    if (domNode) {
      // Initial setup (run immediately and after a short delay to catch async creation)
      addNameToTextareas(domNode)
      setTimeout(() => addNameToTextareas(domNode), 100)
      setTimeout(() => addNameToTextareas(domNode), 500)

      // Periodic check as fallback (Monaco can recreate textareas at any time)
      // Run aggressively every 500ms to catch Monaco's textarea recreation
      intervalRef.current = window.setInterval(() => {
        addNameToTextareas(domNode)
      }, 500) // Check every 500ms

      // Observe for dynamically added textareas (Monaco recreates them)
      observerRef.current = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
          if (mutation.type === 'childList' || mutation.type === 'attributes') {
            mutation.addedNodes.forEach((node) => {
              if (node instanceof HTMLElement) {
                // Check if the added node is a textarea or contains textareas
                if (node.matches?.('textarea.inputarea')) {
                  if (!node.getAttribute('name')) {
                    node.setAttribute('name', 'monaco_editor_content')
                  }
                  if (!node.getAttribute('id')) {
                    node.setAttribute('id', `monaco_editor_textarea_${Date.now()}`)
                  }
                } else {
                  addNameToTextareas(node)
                }
              }
            })
            // Also check the mutation target in case attributes changed
            if (mutation.target instanceof HTMLElement) {
              addNameToTextareas(mutation.target)
            }
          }
        }
      })

      // Start observing with broader configuration
      observerRef.current.observe(domNode, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ['class', 'style'] // Monaco might change these when recreating
      })
    }

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

  // Cleanup observer and interval on unmount
  useEffect(() => {
    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect()
      }
      if (intervalRef.current !== null) {
        window.clearInterval(intervalRef.current)
      }
    }
  }, [])

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
