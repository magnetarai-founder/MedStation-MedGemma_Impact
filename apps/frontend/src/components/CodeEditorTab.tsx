import { useState, useEffect, useCallback } from 'react'
import Editor from '@monaco-editor/react'
import { FileCode, FolderOpen, Plus, FolderPlus, RefreshCw, X } from 'lucide-react'
import { codeEditorApi, type Workspace, type CodeFile, type FileTreeNode } from '../api/codeEditor'

export function CodeEditorTab() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [fileTree, setFileTree] = useState<FileTreeNode[]>([])
  const [openFiles, setOpenFiles] = useState<Map<string, CodeFile>>(new Map())
  const [activeFileId, setActiveFileId] = useState<string | null>(null)
  const [isDirty, setIsDirty] = useState<Set<string>>(new Set())
  const [showWorkspaceModal, setShowWorkspaceModal] = useState(false)
  const [scratchPad, setScratchPad] = useState<string>('// Start coding here...\n')
  const [isScratchPadDirty, setIsScratchPadDirty] = useState(false)

  // Load workspaces on mount
  useEffect(() => {
    loadWorkspaces()
  }, [])

  // Load file tree when workspace changes
  useEffect(() => {
    if (workspace) {
      loadFileTree()
    }
  }, [workspace])

  const loadWorkspaces = async () => {
    try {
      const ws = await codeEditorApi.listWorkspaces()
      setWorkspaces(ws)
    } catch (error) {
      console.error('Failed to load workspaces:', error)
    }
  }

  const loadFileTree = async () => {
    if (!workspace) return
    try {
      const tree = await codeEditorApi.getWorkspaceFiles(workspace.id)
      setFileTree(tree)
    } catch (error) {
      console.error('Failed to load file tree:', error)
    }
  }

  const handleOpenDiskWorkspace = async () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.webkitdirectory = true
    input.onchange = async (e) => {
      const files = (e.target as HTMLInputElement).files
      if (files && files.length > 0) {
        const path = files[0].webkitRelativePath.split('/')[0]
        const fullPath = (files[0] as any).path || ''
        const dirPath = fullPath.substring(0, fullPath.lastIndexOf('/'))

        try {
          const ws = await codeEditorApi.openDiskWorkspace(path, dirPath)
          setWorkspace(ws)
          setShowWorkspaceModal(false)
        } catch (error) {
          console.error('Failed to open workspace:', error)
          alert('Failed to open workspace: ' + error)
        }
      }
    }
    input.click()
  }

  const handleOpenDatabaseWorkspace = async (workspaceId: string) => {
    try {
      const ws = await codeEditorApi.openDatabaseWorkspace(workspaceId)
      setWorkspace(ws)
      setShowWorkspaceModal(false)
    } catch (error) {
      console.error('Failed to open workspace:', error)
    }
  }

  const handleOpenFile = async (fileId: string) => {
    if (openFiles.has(fileId)) {
      setActiveFileId(fileId)
      return
    }

    try {
      const file = await codeEditorApi.getFile(fileId)
      setOpenFiles(new Map(openFiles).set(fileId, file))
      setActiveFileId(fileId)
    } catch (error) {
      console.error('Failed to open file:', error)
    }
  }

  const handleCloseFile = (fileId: string) => {
    const newOpenFiles = new Map(openFiles)
    newOpenFiles.delete(fileId)
    setOpenFiles(newOpenFiles)

    if (activeFileId === fileId) {
      const remaining = Array.from(newOpenFiles.keys())
      setActiveFileId(remaining.length > 0 ? remaining[0] : null)
    }

    // Clear dirty state
    const newDirty = new Set(isDirty)
    newDirty.delete(fileId)
    setIsDirty(newDirty)
  }

  const handleEditorChange = (value: string | undefined, fileId: string) => {
    if (!value) return

    const file = openFiles.get(fileId)
    if (!file) return

    // Update file content in memory
    const updatedFile = { ...file, content: value }
    setOpenFiles(new Map(openFiles).set(fileId, updatedFile))

    // Mark as dirty
    setIsDirty(new Set(isDirty).add(fileId))
  }

  const handleSaveFile = async (fileId: string) => {
    const file = openFiles.get(fileId)
    if (!file) return

    try {
      await codeEditorApi.updateFile(fileId, { content: file.content })

      // Clear dirty state
      const newDirty = new Set(isDirty)
      newDirty.delete(fileId)
      setIsDirty(newDirty)
    } catch (error) {
      console.error('Failed to save file:', error)
      alert('Failed to save file: ' + error)
    }
  }

  const handleCreateFile = async () => {
    if (!workspace) return

    const fileName = prompt('Enter file name:')
    if (!fileName) return

    try {
      // Detect language from extension
      const ext = fileName.split('.').pop()?.toLowerCase() || 'txt'
      const langMap: Record<string, string> = {
        js: 'javascript', ts: 'typescript', tsx: 'typescript',
        py: 'python', java: 'java', cpp: 'cpp',
        html: 'html', css: 'css', json: 'json',
        md: 'markdown', yaml: 'yaml', yml: 'yaml',
      }
      const language = langMap[ext] || 'plaintext'

      const file = await codeEditorApi.createFile({
        workspace_id: workspace.id,
        name: fileName,
        path: fileName,
        content: '',
        language,
      })

      // Refresh file tree
      await loadFileTree()

      // Open the new file
      setOpenFiles(new Map(openFiles).set(file.id, file))
      setActiveFileId(file.id)
    } catch (error) {
      console.error('Failed to create file:', error)
      alert('Failed to create file: ' + error)
    }
  }

  const handleImportFile = async () => {
    if (!workspace) return

    const input = document.createElement('input')
    input.type = 'file'
    input.multiple = true
    input.onchange = async (e) => {
      const files = (e.target as HTMLInputElement).files
      if (!files) return

      for (const file of Array.from(files)) {
        try {
          await codeEditorApi.importFile(workspace.id, file)
        } catch (error) {
          console.error(`Failed to import ${file.name}:`, error)
        }
      }

      // Refresh file tree
      await loadFileTree()
    }
    input.click()
  }

  const handleSyncWorkspace = async () => {
    if (!workspace || workspace.source_type !== 'disk') return

    try {
      await codeEditorApi.syncWorkspace(workspace.id)
      await loadFileTree()

      // Reload open files
      for (const [fileId] of openFiles) {
        try {
          const file = await codeEditorApi.getFile(fileId)
          setOpenFiles(new Map(openFiles).set(fileId, file))
        } catch (error) {
          // File might have been deleted
          handleCloseFile(fileId)
        }
      }
    } catch (error) {
      console.error('Failed to sync workspace:', error)
    }
  }

  const handleSaveScratchPad = async () => {
    try {
      // Create a default workspace if none exists
      let ws = workspace
      if (!ws) {
        // Create default database workspace
        const defaultWorkspace = await codeEditorApi.createWorkspace({
          name: 'My Workspace',
          source_type: 'database',
        })
        ws = defaultWorkspace
        setWorkspace(ws)
      }

      // Save scratch pad as a file
      const fileName = prompt('Save as:', 'untitled.js')
      if (!fileName) return

      const ext = fileName.split('.').pop()?.toLowerCase() || 'txt'
      const langMap: Record<string, string> = {
        js: 'javascript', ts: 'typescript', tsx: 'typescript',
        py: 'python', java: 'java', cpp: 'cpp',
        html: 'html', css: 'css', json: 'json',
        md: 'markdown', yaml: 'yaml', yml: 'yaml',
      }
      const language = langMap[ext] || 'plaintext'

      const file = await codeEditorApi.createFile({
        workspace_id: ws.id,
        name: fileName,
        path: fileName,
        content: scratchPad,
        language,
      })

      // Refresh file tree and open the new file
      await loadFileTree()
      setOpenFiles(new Map(openFiles).set(file.id, file))
      setActiveFileId(file.id)
      setIsScratchPadDirty(false)
      setScratchPad('// Start coding here...\n')
    } catch (error) {
      console.error('Failed to save scratch pad:', error)
      alert('Failed to save: ' + error)
    }
  }

  const handleCreateFileWithoutWorkspace = async () => {
    try {
      // Create a default workspace if none exists
      let ws = workspace
      if (!ws) {
        const defaultWorkspace = await codeEditorApi.createWorkspace({
          name: 'My Workspace',
          source_type: 'database',
        })
        ws = defaultWorkspace
        setWorkspace(ws)
      }

      // Now create the file
      await handleCreateFile()
    } catch (error) {
      console.error('Failed to create file:', error)
      alert('Failed to create file: ' + error)
    }
  }

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd+S or Ctrl+S to save
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault()
        if (activeFileId) {
          handleSaveFile(activeFileId)
        } else if (isScratchPadDirty) {
          handleSaveScratchPad()
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [activeFileId, openFiles, isDirty, isScratchPadDirty])

  const renderFileTree = (nodes: FileTreeNode[], level = 0) => {
    return nodes.map((node) => (
      <div key={node.id} style={{ paddingLeft: `${level * 16}px` }}>
        {node.is_directory ? (
          <>
            <div className="px-2 py-1.5 text-sm text-gray-700 dark:text-gray-300 flex items-center">
              <FolderOpen size={14} className="mr-2" />
              {node.name}
            </div>
            {node.children && renderFileTree(node.children, level + 1)}
          </>
        ) : (
          <div
            className="px-2 py-1.5 rounded text-sm cursor-pointer transition-all hover:bg-white/60 dark:hover:bg-gray-700/60 flex items-center"
            onClick={() => handleOpenFile(node.id)}
          >
            <FileCode size={14} className="mr-2" />
            {node.name}
          </div>
        )}
      </div>
    ))
  }

  const activeFile = activeFileId ? openFiles.get(activeFileId) : null

  // Always show the editor layout
  return (
    <div className="flex h-full w-full">
      {/* File Panel */}
      <div className="w-64 glass border-r border-white/20 dark:border-gray-700/40 flex flex-col">
        <div className="px-4 py-3 border-b border-white/20 dark:border-gray-700/40">
          {workspace ? (
            <>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
                  {workspace.name}
                </h3>
                <button
                  onClick={() => setWorkspace(null)}
                  className="p-1 hover:bg-white/60 dark:hover:bg-gray-700/60 rounded transition-all text-gray-600 dark:text-gray-400"
                  title="Close workspace"
                >
                  <X size={14} />
                </button>
              </div>
              <div className="flex flex-col gap-1">
                <button
                  onClick={handleCreateFile}
                  className="w-full px-2 py-1 text-xs hover:bg-white/60 dark:hover:bg-gray-700/60 rounded transition-all text-gray-700 dark:text-gray-300 text-left"
                >
                  + New File
                </button>
                <button
                  onClick={handleImportFile}
                  className="w-full px-2 py-1 text-xs hover:bg-white/60 dark:hover:bg-gray-700/60 rounded transition-all text-gray-700 dark:text-gray-300 text-left"
                >
                  Import Files
                </button>
                {workspace.source_type === 'disk' && (
                  <button
                    onClick={handleSyncWorkspace}
                    className="w-full px-2 py-1 text-xs hover:bg-white/60 dark:hover:bg-gray-700/60 rounded transition-all text-gray-700 dark:text-gray-300 text-left"
                  >
                    Sync Workspace
                  </button>
                )}
              </div>
            </>
          ) : (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
                Explorer
              </h3>
              <button
                onClick={handleOpenDiskWorkspace}
                className="w-full px-3 py-2 text-sm bg-primary-600 text-white rounded hover:bg-primary-700 transition-colors"
              >
                Open Folder
              </button>
              {isScratchPadDirty && (
                <button
                  onClick={handleSaveScratchPad}
                  className="w-full px-3 py-2 text-sm glass hover:bg-white/60 dark:hover:bg-gray-700/60 rounded transition-colors text-gray-700 dark:text-gray-300"
                >
                  Save Scratch Pad
                </button>
              )}
            </div>
          )}
        </div>

        <div className="flex-1 overflow-auto p-2">
          {workspace ? (
            renderFileTree(fileTree)
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400 text-sm">
              No workspace open
            </div>
          )}
        </div>
      </div>

      {/* Editor Area */}
      <div className="flex-1 flex flex-col">
        {/* Tab Bar */}
        {openFiles.size > 0 && (
          <div className="flex items-center glass border-b border-white/20 dark:border-gray-700/40 overflow-x-auto">
            {Array.from(openFiles.entries()).map(([fileId, file]) => (
              <div
                key={fileId}
                className={`flex items-center gap-2 px-4 py-2 text-sm border-r border-white/20 dark:border-gray-700/40 cursor-pointer ${
                  activeFileId === fileId
                    ? 'bg-transparent text-gray-900 dark:text-gray-100'
                    : 'bg-white/30 dark:bg-gray-800/30 text-gray-600 dark:text-gray-400 hover:bg-white/50 dark:hover:bg-gray-800/50'
                }`}
                onClick={() => setActiveFileId(fileId)}
              >
                <span>{file.name}</span>
                {isDirty.has(fileId) && (
                  <span className="w-2 h-2 rounded-full bg-primary-600"></span>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    handleCloseFile(fileId)
                  }}
                  className="hover:bg-gray-200 dark:hover:bg-gray-700 rounded p-0.5"
                >
                  <X size={12} />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Monaco Editor */}
        {activeFile ? (
          <div className="flex-1">
            <Editor
              height="100%"
              language={activeFile.language}
              value={activeFile.content}
              onChange={(value) => handleEditorChange(value, activeFile.id)}
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
              }}
            />
          </div>
        ) : (
          <div className="flex-1">
            <Editor
              height="100%"
              language="javascript"
              value={scratchPad}
              onChange={(value) => {
                setScratchPad(value || '')
                setIsScratchPadDirty(true)
              }}
              theme="vs-dark"
              options={{
                fontSize: 14,
                fontFamily: "'Fira Code', 'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace",
                fontLigatures: true,
                lineNumbers: 'on',
                minimap: { enabled: false },
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
              }}
            />
          </div>
        )}
      </div>

      {/* Database workspaces modal */}
      {showWorkspaceModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowWorkspaceModal(false)}>
          <div className="glass p-6 rounded-lg max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold mb-4 text-gray-900 dark:text-gray-100">
              Saved Workspaces
            </h3>
            {workspaces.length === 0 ? (
              <p className="text-gray-600 dark:text-gray-400 text-sm">
                No saved workspaces found
              </p>
            ) : (
              <div className="space-y-2 max-h-96 overflow-auto">
                {workspaces.map((ws) => (
                  <div
                    key={ws.id}
                    className="p-3 hover:bg-white/60 dark:hover:bg-gray-700/60 rounded cursor-pointer transition-colors"
                    onClick={() => handleOpenDatabaseWorkspace(ws.id)}
                  >
                    <div className="font-medium text-gray-900 dark:text-gray-100">
                      {ws.name}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {ws.source_type === 'disk' ? `Disk: ${ws.disk_path}` : 'Database'}
                    </div>
                  </div>
                ))}
              </div>
            )}
            <button
              onClick={() => setShowWorkspaceModal(false)}
              className="mt-4 w-full px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors text-gray-900 dark:text-gray-100"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
