import { useState } from 'react'
import Editor from '@monaco-editor/react'
import { Play, Save, FileCode, FolderOpen, Download } from 'lucide-react'

const SUPPORTED_LANGUAGES = [
  { value: 'javascript', label: 'JavaScript' },
  { value: 'typescript', label: 'TypeScript' },
  { value: 'python', label: 'Python' },
  { value: 'java', label: 'Java' },
  { value: 'csharp', label: 'C#' },
  { value: 'cpp', label: 'C++' },
  { value: 'go', label: 'Go' },
  { value: 'rust', label: 'Rust' },
  { value: 'sql', label: 'SQL' },
  { value: 'json', label: 'JSON' },
  { value: 'html', label: 'HTML' },
  { value: 'css', label: 'CSS' },
  { value: 'markdown', label: 'Markdown' },
  { value: 'yaml', label: 'YAML' },
  { value: 'xml', label: 'XML' },
]

export function CodeEditorTab() {
  const [code, setCode] = useState('// Start coding...\n')
  const [language, setLanguage] = useState('javascript')
  const [fileName, setFileName] = useState('untitled')

  const handleEditorChange = (value: string | undefined) => {
    setCode(value || '')
  }

  const handleSave = () => {
    const blob = new Blob([code], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${fileName}.${getFileExtension(language)}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleOpenFile = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.js,.ts,.py,.java,.cs,.cpp,.go,.rs,.sql,.json,.html,.css,.md,.yaml,.yml,.xml'
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (file) {
        const reader = new FileReader()
        reader.onload = (event) => {
          const content = event.target?.result as string
          setCode(content)
          setFileName(file.name.split('.')[0])
          // Auto-detect language from file extension
          const ext = file.name.split('.').pop()?.toLowerCase()
          const detectedLang = detectLanguage(ext || '')
          if (detectedLang) setLanguage(detectedLang)
        }
        reader.readAsText(file)
      }
    }
    input.click()
  }

  const detectLanguage = (extension: string): string => {
    const langMap: Record<string, string> = {
      js: 'javascript',
      ts: 'typescript',
      py: 'python',
      java: 'java',
      cs: 'csharp',
      cpp: 'cpp',
      go: 'go',
      rs: 'rust',
      sql: 'sql',
      json: 'json',
      html: 'html',
      css: 'css',
      md: 'markdown',
      yaml: 'yaml',
      yml: 'yaml',
      xml: 'xml',
    }
    return langMap[extension] || 'javascript'
  }

  const getFileExtension = (lang: string): string => {
    const extMap: Record<string, string> = {
      javascript: 'js',
      typescript: 'ts',
      python: 'py',
      java: 'java',
      csharp: 'cs',
      cpp: 'cpp',
      go: 'go',
      rust: 'rs',
      sql: 'sql',
      json: 'json',
      html: 'html',
      css: 'css',
      markdown: 'md',
      yaml: 'yaml',
      xml: 'xml',
    }
    return extMap[lang] || 'txt'
  }

  return (
    <div className="flex flex-col h-full">
      {/* Minimal Top Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 glass border-b border-white/20 dark:border-gray-700/40">
        {/* Left: File info */}
        <div className="flex items-center gap-3">
          <input
            type="text"
            value={fileName}
            onChange={(e) => setFileName(e.target.value)}
            className="bg-transparent border-none outline-none text-sm font-medium text-gray-700 dark:text-gray-300 w-32 focus:w-48 transition-all"
            placeholder="File name"
          />
          <span className="text-xs text-gray-500 dark:text-gray-500">
            .{getFileExtension(language)}
          </span>
        </div>

        {/* Center: Language selector */}
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          className="px-3 py-1.5 text-sm rounded-lg bg-white/60 dark:bg-gray-800/60 text-gray-700 dark:text-gray-300 border border-gray-300/50 dark:border-gray-600/50 focus:outline-none focus:ring-2 focus:ring-primary-500/50 transition-all"
        >
          {SUPPORTED_LANGUAGES.map((lang) => (
            <option key={lang.value} value={lang.value}>
              {lang.label}
            </option>
          ))}
        </select>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleOpenFile}
            className="p-2 hover:bg-white/60 dark:hover:bg-gray-700/60 rounded-lg transition-all text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400"
            title="Open file"
          >
            <FolderOpen size={18} />
          </button>
          <button
            onClick={handleSave}
            className="p-2 hover:bg-white/60 dark:hover:bg-gray-700/60 rounded-lg transition-all text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400"
            title="Download file"
          >
            <Download size={18} />
          </button>
        </div>
      </div>

      {/* Monaco Editor */}
      <div className="flex-1">
        <Editor
          height="100%"
          language={language}
          value={code}
          onChange={handleEditorChange}
          theme="vs-dark"
          options={{
            fontSize: 14,
            fontFamily: "'Fira Code', 'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace",
            fontLigatures: true,
            lineNumbers: 'on',
            minimap: { enabled: true },
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 2,
            wordWrap: 'on',
            smoothScrolling: true,
            cursorBlinking: 'smooth',
            cursorSmoothCaretAnimation: 'on',
            renderLineHighlight: 'all',
            bracketPairColorization: { enabled: true },
            guides: {
              bracketPairs: true,
              indentation: true,
            },
            padding: { top: 16, bottom: 16 },
            suggest: {
              showMethods: true,
              showFunctions: true,
              showConstructors: true,
              showFields: true,
              showVariables: true,
              showClasses: true,
              showStructs: true,
              showInterfaces: true,
              showModules: true,
              showProperties: true,
              showEvents: true,
              showOperators: true,
              showUnits: true,
              showValues: true,
              showConstants: true,
              showEnums: true,
              showEnumMembers: true,
              showKeywords: true,
              showWords: true,
              showColors: true,
              showFiles: true,
              showReferences: true,
              showFolders: true,
              showTypeParameters: true,
              showSnippets: true,
            },
          }}
        />
      </div>
    </div>
  )
}
