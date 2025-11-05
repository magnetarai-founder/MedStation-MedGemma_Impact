/**
 * CodeView - Main code editing view with split panes
 *
 * Layout:
 * - Left Pane: File browser / Chat history
 * - Right Pane: Monaco editor / Chat pane
 */

import { useState, useEffect } from 'react'
import { FolderTree, MessageSquare, FileCode } from 'lucide-react'
import { ResizableSidebar } from './ResizableSidebar'
import { FileBrowser } from './FileBrowser'
import { MonacoEditor } from './MonacoEditor'

export function CodeView() {
  const [leftView, setLeftView] = useState<'files' | 'chats'>('files')
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [fileContent, setFileContent] = useState<string>('')
  const [fileLanguage, setFileLanguage] = useState<string>('typescript')
  const [loading, setLoading] = useState(false)

  const loadFile = async (path: string) => {
    setLoading(true)
    setSelectedFile(path)

    try {
      const res = await fetch(`/api/v1/code/read?path=${encodeURIComponent(path)}`)

      if (!res.ok) {
        throw new Error('Failed to load file')
      }

      const data = await res.json()
      setFileContent(data.content || '')

      // Detect language from file extension
      const ext = path.split('.').pop()?.toLowerCase()
      const languageMap: Record<string, string> = {
        'ts': 'typescript',
        'tsx': 'typescript',
        'js': 'javascript',
        'jsx': 'javascript',
        'py': 'python',
        'rs': 'rust',
        'go': 'go',
        'java': 'java',
        'cpp': 'cpp',
        'c': 'c',
        'cs': 'csharp',
        'rb': 'ruby',
        'php': 'php',
        'swift': 'swift',
        'kt': 'kotlin',
        'md': 'markdown',
        'json': 'json',
        'yaml': 'yaml',
        'yml': 'yaml',
        'toml': 'toml',
        'xml': 'xml',
        'html': 'html',
        'css': 'css',
        'scss': 'scss',
        'sql': 'sql',
        'sh': 'shell',
        'bash': 'shell',
      }

      setFileLanguage(languageMap[ext || ''] || 'plaintext')
    } catch (err) {
      console.error('Error loading file:', err)
      setFileContent(`Error loading file: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <ResizableSidebar
      initialWidth={280}
      minWidth={200}
      storageKey="ns.codeViewSidebarWidth"
      left={
        <div className="h-full flex flex-col bg-gray-50 dark:bg-gray-900">
          {/* Left Pane Header */}
          <div className="p-3 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-1">
              <button
                onClick={() => setLeftView('files')}
                className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-md transition-all ${
                  leftView === 'files'
                    ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 font-medium'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700/50'
                }`}
              >
                <FolderTree className="w-4 h-4" />
                <span>Files</span>
              </button>

              <button
                onClick={() => setLeftView('chats')}
                className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-md transition-all ${
                  leftView === 'chats'
                    ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 font-medium'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700/50'
                }`}
              >
                <MessageSquare className="w-4 h-4" />
                <span>Chats</span>
              </button>
            </div>
          </div>

          {/* Left Pane Content */}
          <div className="flex-1 overflow-auto">
            {leftView === 'files' && (
              <FileBrowser onFileSelect={loadFile} selectedFile={selectedFile} />
            )}

            {leftView === 'chats' && (
              <div className="p-4 space-y-2">
                <div className="text-center space-y-2 mt-20">
                  <MessageSquare className="w-12 h-12 mx-auto text-gray-400 dark:text-gray-600" />
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Chat history
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-500">
                    Phase 4: Chat Integration
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      }
      right={
        <div className="h-full flex flex-col bg-gray-50 dark:bg-gray-900">
          {selectedFile ? (
            <>
              {/* File header */}
              <div className="border-b border-gray-200 dark:border-gray-700 px-4 py-2 bg-white dark:bg-gray-800">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileCode className="w-4 h-4 text-gray-500" />
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      {selectedFile}
                    </span>
                  </div>
                  <span className="text-xs text-gray-500 px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded">
                    Read-only
                  </span>
                </div>
              </div>

              {/* Monaco Editor */}
              <div className="flex-1">
                {loading ? (
                  <div className="h-full flex items-center justify-center">
                    <div className="text-sm text-gray-500">Loading...</div>
                  </div>
                ) : (
                  <MonacoEditor
                    value={fileContent}
                    language={fileLanguage}
                    readOnly={true}
                    theme="vs-dark"
                  />
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center space-y-4">
                <FileCode className="w-16 h-16 mx-auto text-gray-400 dark:text-gray-600" />
                <div className="space-y-2">
                  <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
                    Monaco Editor
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Select a file to view
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-500">
                    Phase 2: Read-Only File Viewing
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      }
    />
  )
}
