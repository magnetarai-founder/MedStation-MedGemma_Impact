/**
 * CodeView - Main code editing view with split panes
 *
 * Layout:
 * - Left Pane: File browser / Chat history
 * - Right Pane: Monaco editor / Chat pane
 */

import { useState, useEffect } from 'react'
import { FolderTree, MessageSquare, FileCode, Save, Edit3 } from 'lucide-react'
import { ResizableSidebar } from './ResizableSidebar'
import { FileBrowser } from './FileBrowser'
import { MonacoEditor } from './MonacoEditor'
import { DiffPreviewModal } from './DiffPreviewModal'
import { CodeChat } from './CodeChat'
import toast from 'react-hot-toast'
import { authFetch } from '@/lib/api'

export function CodeView() {
  const [leftView, setLeftView] = useState<'files' | 'chats'>('files')
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [fileContent, setFileContent] = useState<string>('')
  const [originalContent, setOriginalContent] = useState<string>('')
  const [fileLanguage, setFileLanguage] = useState<string>('typescript')
  const [loading, setLoading] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [showDiffPreview, setShowDiffPreview] = useState(false)
  const [diffData, setDiffData] = useState<any>(null)

  const loadFile = async (path: string, isAbsolute: boolean = false) => {
    setLoading(true)
    setSelectedFile(path)

    try {
      const url = isAbsolute
        ? `/api/v1/code/read?path=${encodeURIComponent(path)}&absolute_path=true`
        : `/api/v1/code/read?path=${encodeURIComponent(path)}`

      const res = await authFetch(url)

      if (!res.ok) {
        throw new Error('Failed to load file')
      }

      const data = await res.json()
      const content = data.content || ''
      setFileContent(content)
      setOriginalContent(content)
      setIsEditing(false)
      setHasChanges(false)

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

  const handleContentChange = (newContent: string) => {
    setFileContent(newContent)
    setHasChanges(newContent !== originalContent)
  }

  const handleSaveClick = async () => {
    if (!selectedFile || !hasChanges) return

    try {
      // Get diff preview
      const res = await authFetch('/api/v1/code/diff/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: selectedFile,
          new_content: fileContent
        })
      })

      if (!res.ok) {
        throw new Error('Failed to generate diff')
      }

      const diff = await res.json()
      setDiffData(diff)
      setShowDiffPreview(true)
    } catch (err) {
      console.error('Error generating diff:', err)
      toast.error('Failed to preview changes')
    }
  }

  const handleConfirmSave = async () => {
    if (!selectedFile) return

    try {
      const res = await authFetch('/api/v1/code/write', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: selectedFile,
          content: fileContent,
          create_if_missing: false
        })
      })

      if (!res.ok) {
        throw new Error('Failed to save file')
      }

      const result = await res.json()

      // Update original content
      setOriginalContent(fileContent)
      setHasChanges(false)
      setShowDiffPreview(false)

      toast.success(`Saved ${selectedFile}`)

      // Show risk assessment if present
      if (result.risk_assessment) {
        console.log('Risk assessment:', result.risk_assessment)
      }
    } catch (err) {
      console.error('Error saving file:', err)
      toast.error('Failed to save file')
    }
  }

  const toggleEditMode = () => {
    if (isEditing && hasChanges) {
      // Warn about unsaved changes
      if (!confirm('You have unsaved changes. Discard them?')) {
        return
      }
      setFileContent(originalContent)
      setHasChanges(false)
    }
    setIsEditing(!isEditing)
  }

  return (
    <>
    <ResizableSidebar
      initialWidth={280}
      minWidth={200}
      storageKey="ns.codeViewSidebarWidth"
      left={
        <div className="h-full flex flex-col bg-white dark:bg-gray-900">
          {/* Left Pane Header */}
          <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-1">
              <button
                onClick={() => setLeftView('files')}
                className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition-all ${
                  leftView === 'files'
                    ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 font-medium'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800/50'
                }`}
              >
                <FolderTree className="w-4 h-4" />
                <span>Files</span>
              </button>

              <button
                onClick={() => setLeftView('chats')}
                className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition-all ${
                  leftView === 'chats'
                    ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 font-medium'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800/50'
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
        <div className="h-full flex flex-col bg-white dark:bg-gray-900">
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
                    {hasChanges && (
                      <span className="text-xs text-orange-600 dark:text-orange-400">
                        • Modified
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {isEditing ? (
                      <>
                      <button
                        onClick={handleSaveClick}
                        disabled={!hasChanges}
                        className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                          hasChanges
                            ? 'bg-primary-600 hover:bg-primary-700 text-white'
                            : 'bg-gray-200 dark:bg-gray-700 text-gray-400 cursor-not-allowed'
                          }`}
                      >
                        <Save className="w-3.5 h-3.5" />
                        Save
                      </button>
                      <button
                        onClick={toggleEditMode}
                        className="px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg transition-colors"
                      >
                        Cancel
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={toggleEditMode}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg transition-colors"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                      Edit
                    </button>
                  )}
                </div>
              </div>
              </div>

              {/* Monaco Editor */}
              <div className="flex-1 min-h-0">
                {loading ? (
                  <div className="h-full flex items-center justify-center">
                    <div className="text-sm text-gray-500">Loading...</div>
                  </div>
                ) : (
                  <MonacoEditor
                    value={fileContent}
                    language={fileLanguage}
                    readOnly={!isEditing}
                    onValueChange={handleContentChange}
                    theme="vs-dark"
                  />
                )}
              </div>

              {/* Chat - Fixed height at bottom */}
              <div className="h-80 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
                <CodeChat currentFile={selectedFile} fileContent={fileContent} />
              </div>
            </>
          ) : (
            <>
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

              {/* Chat - Fixed height at bottom */}
              <div className="h-80 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
                <CodeChat currentFile={null} fileContent="" />
              </div>
            </>
          )}
        </div>
      }
    />

    {/* Diff Preview Modal */}
    {showDiffPreview && diffData && (
      <DiffPreviewModal
        isOpen={showDiffPreview}
        onClose={() => setShowDiffPreview(false)}
        onConfirm={handleConfirmSave}
        diffText={diffData.diff}
        stats={diffData.stats}
        filePath={selectedFile || ''}
      />
    )}
  </>
  )
}
