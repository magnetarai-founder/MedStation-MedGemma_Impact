/**
 * Lightweight Rich Text Editor
 *
 * Simple WYSIWYG editor with basic formatting toolbar
 * Uses contentEditable for zero dependencies
 */

import { useRef, useEffect, useState } from 'react'
import DOMPurify from 'dompurify'
import {
  Bold,
  Italic,
  Underline,
  List,
  ListOrdered,
  AlignLeft,
  AlignCenter,
  AlignRight,
  Link as LinkIcon,
  Code,
  Quote,
} from 'lucide-react'

interface RichTextEditorProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
  disabled?: boolean
}

export function RichTextEditor({
  value,
  onChange,
  placeholder = 'Start writing...',
  className = '',
  disabled = false,
}: RichTextEditorProps) {
  const editorRef = useRef<HTMLDivElement>(null)
  const [isFocused, setIsFocused] = useState(false)

  // Set initial content (sanitized to prevent XSS)
  useEffect(() => {
    if (editorRef.current && editorRef.current.innerHTML !== value) {
      const sanitized = DOMPurify.sanitize(value || '', {
        ALLOWED_TAGS: ['b', 'i', 'u', 'strong', 'em', 'p', 'br', 'ul', 'ol', 'li', 'a', 'code', 'pre'],
        ALLOWED_ATTR: ['href', 'target']
      })
      editorRef.current.innerHTML = sanitized
    }
  }, [value])

  const handleInput = () => {
    if (editorRef.current) {
      const html = editorRef.current.innerHTML
      onChange(html)
    }
  }

  const execCommand = (command: string, value?: string) => {
    document.execCommand(command, false, value)
    editorRef.current?.focus()
  }

  const insertLink = () => {
    const url = prompt('Enter URL:')
    if (url) {
      execCommand('createLink', url)
    }
  }

  const formatButtons = [
    { icon: Bold, command: 'bold', title: 'Bold (Cmd+B)' },
    { icon: Italic, command: 'italic', title: 'Italic (Cmd+I)' },
    { icon: Underline, command: 'underline', title: 'Underline (Cmd+U)' },
    { icon: Code, command: 'formatBlock', value: 'pre', title: 'Code Block' },
    { icon: Quote, command: 'formatBlock', value: 'blockquote', title: 'Quote' },
    { icon: List, command: 'insertUnorderedList', title: 'Bullet List' },
    { icon: ListOrdered, command: 'insertOrderedList', title: 'Numbered List' },
    { icon: AlignLeft, command: 'justifyLeft', title: 'Align Left' },
    { icon: AlignCenter, command: 'justifyCenter', title: 'Align Center' },
    { icon: AlignRight, command: 'justifyRight', title: 'Align Right' },
  ]

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Toolbar */}
      <div
        className={`flex items-center gap-1 p-2 border-b bg-gray-50 dark:bg-gray-900/50 transition-colors ${
          isFocused
            ? 'border-gray-300 dark:border-gray-600'
            : 'border-gray-200 dark:border-gray-700'
        }`}
      >
        {formatButtons.map((btn, idx) => {
          const Icon = btn.icon
          return (
            <button
              key={idx}
              type="button"
              onClick={() => execCommand(btn.command, btn.value)}
              disabled={disabled}
              className="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title={btn.title}
            >
              <Icon className="w-4 h-4" />
            </button>
          )
        })}

        {/* Link Button */}
        <button
          type="button"
          onClick={insertLink}
          disabled={disabled}
          className="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          title="Insert Link"
        >
          <LinkIcon className="w-4 h-4" />
        </button>

        {/* Heading Dropdown */}
        <select
          onChange={(e) => execCommand('formatBlock', e.target.value)}
          disabled={disabled}
          className="ml-2 px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 disabled:opacity-50"
          defaultValue="p"
        >
          <option value="p">Paragraph</option>
          <option value="h1">Heading 1</option>
          <option value="h2">Heading 2</option>
          <option value="h3">Heading 3</option>
          <option value="h4">Heading 4</option>
        </select>
      </div>

      {/* Editor Area */}
      <div
        ref={editorRef}
        contentEditable={!disabled}
        onInput={handleInput}
        onFocus={() => setIsFocused(true)}
        onBlur={() => setIsFocused(false)}
        className={`flex-1 p-4 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none transition-colors overflow-auto prose prose-sm dark:prose-invert max-w-none ${
          isFocused
            ? 'ring-2 ring-primary-500'
            : ''
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        data-placeholder={placeholder}
      />

      <style>{`
        [contenteditable]:empty:before {
          content: attr(data-placeholder);
          color: #9ca3af;
          pointer-events: none;
          position: absolute;
        }

        [contenteditable] {
          outline: none;
        }

        /* Styling for formatted content */
        [contenteditable] h1 {
          font-size: 2em;
          font-weight: bold;
          margin: 0.67em 0;
        }

        [contenteditable] h2 {
          font-size: 1.5em;
          font-weight: bold;
          margin: 0.75em 0;
        }

        [contenteditable] h3 {
          font-size: 1.17em;
          font-weight: bold;
          margin: 0.83em 0;
        }

        [contenteditable] h4 {
          font-size: 1em;
          font-weight: bold;
          margin: 1em 0;
        }

        [contenteditable] blockquote {
          border-left: 4px solid #d1d5db;
          padding-left: 1em;
          margin: 1em 0;
          color: #6b7280;
        }

        .dark [contenteditable] blockquote {
          border-left-color: #4b5563;
          color: #9ca3af;
        }

        [contenteditable] pre {
          background: #f3f4f6;
          padding: 1em;
          border-radius: 0.5em;
          overflow-x: auto;
          font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
          font-size: 0.875em;
        }

        .dark [contenteditable] pre {
          background: #1f2937;
        }

        [contenteditable] a {
          color: #3b82f6;
          text-decoration: underline;
        }

        .dark [contenteditable] a {
          color: #60a5fa;
        }

        [contenteditable] ul,
        [contenteditable] ol {
          padding-left: 2em;
          margin: 1em 0;
        }

        [contenteditable] li {
          margin: 0.5em 0;
        }
      `}</style>
    </div>
  )
}
