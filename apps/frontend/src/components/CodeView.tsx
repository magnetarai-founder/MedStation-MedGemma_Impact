/**
 * CodeView - Main code editing view with split panes
 *
 * Layout:
 * - Left Pane: File browser / Chat history
 * - Right Pane: Monaco editor / Chat pane
 */

import { useState, useEffect } from 'react'
import { FolderTree, MessageSquare, FileCode, Save, Edit3, Terminal as TerminalIcon } from 'lucide-react'
import { ResizableSidebar } from './ResizableSidebar'
import { FileBrowser } from './FileBrowser'
import { MonacoEditor } from './MonacoEditor'
import { DiffConfirmModal } from './DiffConfirmModal'
import { TerminalPanel } from './TerminalPanel'
import { CodeChat } from './CodeChat'
import toast from 'react-hot-toast'
import { codeEditorApi } from '@/api/codeEditor'

export function CodeView() {
  const [leftView, setLeftView] = useState<'files' | 'chats'>('files')
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null)
  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null)
  const [fileContent, setFileContent] = useState<string>('')
  const [originalContent, setOriginalContent] = useState<string>('')
  const [fileLanguage, setFileLanguage] = useState<string>('typescript')
  const [baseUpdatedAt, setBaseUpdatedAt] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [showDiffPreview, setShowDiffPreview] = useState(false)
  const [diffData, setDiffData] = useState<any>(null)
  const [permissionError, setPermissionError] = useState<string | null>(null)
  const [terminalOpen, setTerminalOpen] = useState(false)

  const loadFile = async (fileId: string, filePath: string) => {
    setLoading(true)
    setSelectedFileId(fileId)
    setSelectedFilePath(filePath)
    setPermissionError(null)

    try {
      const file = await codeEditorApi.getFile(fileId)
      setFileContent(file.content || '')
      setOriginalContent(file.content || '')
      setFileLanguage(file.language || 'plaintext')
      setBaseUpdatedAt(file.updated_at || null)
      setIsEditing(false)
      setHasChanges(false)
    } catch (err: any) {
      if (err?.status === 403) {
        setPermissionError('Permission denied: code.use required')
      } else {
        console.error('Error loading file:', err)
        setFileContent(`Error loading file: ${err instanceof Error ? err.message : 'Unknown error'}`)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleContentChange = (newContent: string) => {
    setFileContent(newContent)
    setHasChanges(newContent !== originalContent)
  }

  const handleSaveClick = async () => {
    if (!selectedFileId || !hasChanges) return

    try {
      const diffResp = await codeEditorApi.diffFile(
        selectedFileId,
        fileContent,
        baseUpdatedAt || undefined
      )
      setDiffData(diffResp)
      setShowDiffPreview(true)
    } catch (err: any) {
      if (err?.status === 403) {
        setPermissionError('Permission denied: code.use required')
      } else {
        console.error('Error generating diff:', err)
        toast.error('Failed to preview changes')
      }
    }
  }

  const handleConfirmSave = async () => {
    if (!selectedFileId) return

    try {
      const updated = await codeEditorApi.updateFile(selectedFileId, {
        content: fileContent,
        base_updated_at: baseUpdatedAt || undefined,
      })

      // Success - update state
      setOriginalContent(fileContent)
      setBaseUpdatedAt(updated.updated_at)
      setHasChanges(false)
      setShowDiffPreview(false)
      toast.success(`Saved ${selectedFilePath}`)
    } catch (err: any) {
      if (err?.status === 409) {
        // Conflict - reload and show fresh diff
        toast.error('File was modified by another user')
        setShowDiffPreview(false)

        try {
          const fresh = await codeEditorApi.getFile(selectedFileId)
          const freshDiff = await codeEditorApi.diffFile(
            selectedFileId,
            fileContent,
            fresh.updated_at
          )
          setDiffData({
            ...freshDiff,
            conflictWarning: `File changed (current: ${fresh.updated_at})`,
          })
          setShowDiffPreview(true)
        } catch (refetchErr) {
          console.error('Error refetching after conflict:', refetchErr)
        }
      } else if (err?.status === 403) {
        setPermissionError('Permission denied: code.edit required')
        setShowDiffPreview(false)
      } else {
        console.error('Error saving file:', err)
        toast.error('Failed to save file')
      }
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

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl+S: Save with diff modal
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault()
        if (isEditing && hasChanges && selectedFileId) {
          handleSaveClick()
        }
      }

      // Cmd/Ctrl+/: Toggle terminal
      if ((e.metaKey || e.ctrlKey) && e.key === '/') {
        e.preventDefault()
        setTerminalOpen((prev) => !prev)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isEditing, hasChanges, selectedFileId])

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
              <FileBrowser onFileSelect={loadFile} selectedFileId={selectedFileId} />
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
          {/* Permission Error Banner */}
          {permissionError && (
            <div className="bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800 px-4 py-2 flex items-center justify-between">
              <span className="text-sm text-red-800 dark:text-red-200">{permissionError}</span>
              <button
                onClick={() => setPermissionError(null)}
                className="text-red-600 hover:text-red-800 dark:text-red-400"
              >
                ✕
              </button>
            </div>
          )}

          {selectedFileId ? (
            <>
              {/* File header */}
              <div className="border-b border-gray-200 dark:border-gray-700 px-4 py-2 bg-white dark:bg-gray-800">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileCode className="w-4 h-4 text-gray-500" />
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      {selectedFilePath}
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
                  <button
                    onClick={() => setTerminalOpen((v) => !v)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg transition-colors"
                  >
                    <TerminalIcon className="w-3.5 h-3.5" />
                    Terminal
                  </button>
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

              {/* Terminal Panel */}
              {terminalOpen && (
                <TerminalPanel isOpen={terminalOpen} onClose={() => setTerminalOpen(false)} />
              )}

              {/* Chat - Fixed height at bottom */}
              <div className="h-80 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
                <CodeChat currentFile={selectedFilePath} fileContent={fileContent} />
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

    {/* Diff Confirm Modal */}
    {showDiffPreview && diffData && (
      <DiffConfirmModal
        isOpen={showDiffPreview}
        onClose={() => setShowDiffPreview(false)}
        onConfirm={handleConfirmSave}
        diffText={diffData.diff}
        filePath={selectedFilePath || ''}
        conflictWarning={diffData.conflictWarning}
        truncated={diffData.truncated}
        truncationMessage={diffData.message}
      />
    )}
  </>
  )
}
