/**
 * FileBrowser - File tree navigation for Code Tab
 * Uses code-editor API with workspace-based file management
 */

import { useState, useEffect } from 'react'
import { Folder, File, ChevronRight, ChevronDown, RefreshCw, FolderOpen, FilePlus } from 'lucide-react'
import toast from 'react-hot-toast'
import { codeEditorApi, type FileTreeNode } from '@/api/codeEditor'

interface FileBrowserProps {
  onFileSelect: (fileId: string, filePath: string) => void
  selectedFileId: string | null
}

export function FileBrowser({ onFileSelect, selectedFileId }: FileBrowserProps) {
  const [tree, setTree] = useState<FileTreeNode[]>([])
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [workspaceId, setWorkspaceId] = useState<string | null>(null)
  const [workspacePath, setWorkspacePath] = useState<string | null>(null)
  const [showNewFileModal, setShowNewFileModal] = useState(false)
  const [newFileName, setNewFileName] = useState('')
  const [creating, setCreating] = useState(false)

  // Build flat file ID map for quick lookup
  const [fileIdMap, setFileIdMap] = useState<Map<string, string>>(new Map())

  const buildFileIdMap = (nodes: FileTreeNode[]): Map<string, string> => {
    const map = new Map<string, string>()
    const traverse = (items: FileTreeNode[]) => {
      for (const item of items) {
        if (!item.is_directory) {
          map.set(item.id, item.path)
        }
        if (item.children) {
          traverse(item.children)
        }
      }
    }
    traverse(nodes)
    return map
  }

  const loadFileTree = async (wsId?: string) => {
    const targetWsId = wsId || workspaceId
    if (!targetWsId) {
      setTree([])
      return
    }

    setLoading(true)
    setError(null)

    try {
      const files = await codeEditorApi.listWorkspaceFiles(targetWsId)
      setTree(files || [])
      const idMap = buildFileIdMap(files || [])
      setFileIdMap(idMap)
    } catch (err: any) {
      console.error('Error loading file tree:', err)
      if (err.status === 403) {
        setError('Permission denied: code.use required')
      } else {
        setError(err.message || 'Failed to load files')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleOpenFolder = async () => {
    const defaultVal = localStorage.getItem('ns.code.workspaceRoot') || ''
    const input = prompt('Enter absolute folder path to browse', defaultVal)
    if (!input) return

    try {
      // Open disk workspace
      const workspace = await codeEditorApi.openDiskWorkspace(
        input.split('/').pop() || 'workspace',
        input
      )

      // Save to localStorage
      localStorage.setItem('ns.code.workspaceId', workspace.id)
      localStorage.setItem('ns.code.workspaceRoot', input)
      setWorkspaceId(workspace.id)
      setWorkspacePath(input)

      // Load file tree
      await loadFileTree(workspace.id)
      toast.success('Opened folder')

      // Dispatch event to update project name in sidebar
      window.dispatchEvent(new CustomEvent('workspace-changed', { detail: { path: input } }))
    } catch (err: any) {
      console.error('Error opening folder:', err)
      if (err.status === 403) {
        toast.error('Permission denied: code.edit required')
      } else {
        toast.error('Failed to open folder')
      }
    }
  }

  const handleCreateFile = async () => {
    if (!newFileName.trim()) {
      toast.error('Please enter a file name')
      return
    }

    if (!workspaceId) {
      toast.error('No workspace open')
      return
    }

    setCreating(true)
    try {
      // Detect language from extension
      const ext = newFileName.split('.').pop()?.toLowerCase() || 'txt'
      const langMap: Record<string, string> = {
        js: 'javascript', jsx: 'javascript', ts: 'typescript', tsx: 'typescript',
        py: 'python', java: 'java', cpp: 'cpp', c: 'c', go: 'go', rs: 'rust',
        rb: 'ruby', php: 'php', html: 'html', css: 'css', json: 'json',
        yaml: 'yaml', yml: 'yaml', md: 'markdown', sql: 'sql', sh: 'shell'
      }
      const language = langMap[ext] || 'plaintext'

      const file = await codeEditorApi.createFile({
        workspace_id: workspaceId,
        name: newFileName,
        path: newFileName,
        content: '',
        language
      })

      toast.success(`Created ${newFileName}`)
      setShowNewFileModal(false)
      setNewFileName('')

      // Reload file tree
      await loadFileTree()

      // Open the new file
      onFileSelect(file.id, file.path)
    } catch (err: any) {
      console.error('Error creating file:', err)
      if (err.status === 403) {
        toast.error('Permission denied: code.edit required')
      } else {
        toast.error(err.message || 'Failed to create file')
      }
    } finally {
      setCreating(false)
    }
  }

  useEffect(() => {
    // Load workspace from localStorage
    const savedWsId = localStorage.getItem('ns.code.workspaceId')
    const savedWsPath = localStorage.getItem('ns.code.workspaceRoot')

    if (savedWsId) {
      setWorkspaceId(savedWsId)
      setWorkspacePath(savedWsPath)
      loadFileTree(savedWsId)
    }

    // Listen for 'open-folder' event from CodeSidebar
    const handleOpenFolderEvent = () => {
      handleOpenFolder()
    }
    window.addEventListener('open-folder', handleOpenFolderEvent)

    // Auto-refresh every 500ms when a workspace is open (like VS Code)
    const refreshInterval = setInterval(() => {
      if (workspaceId && !loading) {
        loadFileTree()
      }
    }, 500)

    return () => {
      window.removeEventListener('open-folder', handleOpenFolderEvent)
      clearInterval(refreshInterval)
    }
  }, [workspaceId])

  const toggleExpand = (path: string) => {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(path)) {
        next.delete(path)
      } else {
        next.add(path)
      }
      return next
    })
  }

  const handleFileClick = (node: FileTreeNode) => {
    if (!node.is_directory) {
      onFileSelect(node.id, node.path)
    }
  }

  const renderNode = (node: FileTreeNode, depth: number = 0): JSX.Element => {
    const isExpanded = expanded.has(node.path)
    const isSelected = selectedFileId === node.id
    const paddingLeft = depth * 16

    if (node.is_directory) {
      return (
        <div key={node.id}>
          <button
            onClick={() => toggleExpand(node.path)}
            className={`flex items-center gap-2 py-1.5 px-2 hover:bg-gray-50 dark:hover:bg-gray-800/50 w-full text-left transition-colors ${
              isExpanded ? 'bg-gray-50 dark:bg-gray-800/30' : ''
            }`}
            style={{ paddingLeft: `${paddingLeft + 8}px` }}
          >
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 flex-shrink-0 text-gray-500" />
            ) : (
              <ChevronRight className="w-4 h-4 flex-shrink-0 text-gray-500" />
            )}
            <Folder className="w-4 h-4 flex-shrink-0 text-blue-500" />
            <span className="text-sm text-gray-700 dark:text-gray-300 truncate">{node.name}</span>
          </button>

          {isExpanded && node.children && (
            <div>
              {node.children.map(child => renderNode(child, depth + 1))}
            </div>
          )}
        </div>
      )
    }

    // File node
    return (
      <button
        key={node.id}
        onClick={() => handleFileClick(node)}
        className={`flex items-center gap-2 py-1.5 px-2 hover:bg-gray-50 dark:hover:bg-gray-800/50 w-full text-left transition-colors ${
          isSelected ? 'bg-primary-100 dark:bg-primary-900/30' : ''
        }`}
        style={{ paddingLeft: `${paddingLeft + 28}px` }}
      >
        <File className={`w-4 h-4 flex-shrink-0 ${isSelected ? 'text-primary-600' : 'text-gray-400'}`} />
        <span className={`text-sm truncate ${isSelected ? 'text-primary-700 dark:text-primary-400 font-medium' : 'text-gray-700 dark:text-gray-300'}`}>
          {node.name}
        </span>
      </button>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center space-y-2">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto text-gray-400" />
          <p className="text-sm text-gray-500">Loading files...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 space-y-3">
        <div className="text-sm text-red-600 dark:text-red-400">
          {error}
        </div>
        <button
          onClick={() => loadFileTree()}
          className="flex items-center gap-2 text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400"
        >
          <RefreshCw className="w-4 h-4" />
          Retry
        </button>
      </div>
    )
  }

  if (tree.length === 0) {
    return (
      <div className="h-full flex flex-col">
        <div className="flex-1 overflow-auto p-4">
          <div className="text-center text-sm text-gray-500 py-8">
            <div className="w-12 h-12 mx-auto mb-3 flex items-center justify-center">
              <Folder size={43} strokeWidth={1.5} className="opacity-50" />
            </div>
            <p>No files yet</p>
            <p className="text-xs mt-1">Click "Open Project or Folder" above to browse files</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full overflow-auto">
      {/* Header */}
      <div className="sticky top-0 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-4 py-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wide">
            Files
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setShowNewFileModal(true)}
              className="p-1 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-lg transition-colors"
              title="New File"
            >
              <FilePlus className="w-3.5 h-3.5 text-gray-500" />
            </button>
            <button
              onClick={() => loadFileTree()}
              className="p-1 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-lg transition-colors"
              title="Refresh"
            >
              <RefreshCw className="w-3.5 h-3.5 text-gray-500" />
            </button>
          </div>
        </div>
        {workspacePath && (
          <div className="text-xs text-gray-500 truncate" title={workspacePath}>
            {workspacePath}
          </div>
        )}
      </div>

      {/* File tree */}
      <div className="py-1">
        {tree.map(node => renderNode(node))}
      </div>

      {/* New File Modal */}
      {showNewFileModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-2xl w-full max-w-md">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Create New File
              </h2>
              <p className="text-sm text-gray-500 mt-1">
                {workspacePath ? `In ${workspacePath}` : 'In workspace'}
              </p>
            </div>

            <div className="px-6 py-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                File Name
              </label>
              <input
                type="text"
                value={newFileName}
                onChange={(e) => setNewFileName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleCreateFile()
                  } else if (e.key === 'Escape') {
                    setShowNewFileModal(false)
                    setNewFileName('')
                  }
                }}
                placeholder="example.ts"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                autoFocus
              />
              <p className="text-xs text-gray-500 mt-2">
                Press Enter to create, Escape to cancel
              </p>
            </div>

            <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-end gap-3">
              <button
                onClick={() => {
                  setShowNewFileModal(false)
                  setNewFileName('')
                }}
                disabled={creating}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateFile}
                disabled={creating || !newFileName.trim()}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <FilePlus className="w-4 h-4" />
                {creating ? 'Creating...' : 'Create File'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
