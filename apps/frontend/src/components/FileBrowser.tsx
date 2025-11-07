/**
 * FileBrowser - File tree navigation for Code Tab
 * Uses patterns from Continue's file tree implementation
 */

import { useState, useEffect } from 'react'
import { Folder, File, ChevronRight, ChevronDown, RefreshCw, FolderOpen, FilePlus } from 'lucide-react'
import toast from 'react-hot-toast'
import { authFetch } from '@/lib/api'

interface FileNode {
  name: string
  type: 'file' | 'directory'
  path: string
  size?: number
  children?: FileNode[]
}

interface FileBrowserProps {
  onFileSelect: (path: string, isAbsolute?: boolean) => void
  selectedFile: string | null
}

export function FileBrowser({ onFileSelect, selectedFile }: FileBrowserProps) {
  const [tree, setTree] = useState<FileNode[]>([])
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentPath, setCurrentPath] = useState<string | null>(null)
  const [showNewFileModal, setShowNewFileModal] = useState(false)
  const [newFileName, setNewFileName] = useState('')
  const [creating, setCreating] = useState(false)

  const loadFileTree = async (absolutePath?: string) => {
    setLoading(true)
    setError(null)

    try {
      const url = absolutePath
        ? `/api/v1/code/files?recursive=true&absolute_path=${encodeURIComponent(absolutePath)}`
        : '/api/v1/code/files?recursive=true'

      const res = await authFetch(url)

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}))
        throw new Error(errorData.detail || `Failed to load file tree (${res.status})`)
      }

      const data = await res.json()
      setTree(data.items || [])
      if (absolutePath) {
        setCurrentPath(absolutePath)
      }
    } catch (err) {
      console.error('Error loading file tree:', err)
      setError(err instanceof Error ? err.message : 'Failed to load files')
    } finally {
      setLoading(false)
    }
  }

  const handleOpenFolder = async () => {
    const defaultVal = localStorage.getItem('ns.code.workspaceRoot') || ''
    const input = prompt('Enter absolute folder path to browse', defaultVal)
    if (!input) return

    try {
      // Save to localStorage
      localStorage.setItem('ns.code.workspaceRoot', input)

      // Notify backend of workspace root for git operations
      await authFetch('/api/v1/code/workspace/set', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workspace_root: input })
      })

      // Load file tree
      await loadFileTree(input)
      toast.success('Opened folder')

      // Dispatch event to update project name in sidebar
      window.dispatchEvent(new CustomEvent('workspace-changed', { detail: { path: input } }))
    } catch (err) {
      console.error('Error opening folder:', err)
      toast.error('Failed to open folder')
    }
  }

  const handleCreateFile = async () => {
    if (!newFileName.trim()) {
      toast.error('Please enter a file name')
      return
    }

    setCreating(true)
    try {
      const res = await authFetch('/api/v1/code/write', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: newFileName,
          content: '',
          create_if_missing: true
        })
      })

      if (!res.ok) {
        const error = await res.json().catch(() => ({}))
        throw new Error(error.detail || 'Failed to create file')
      }

      toast.success(`Created ${newFileName}`)
      setShowNewFileModal(false)
      setNewFileName('')

      // Reload file tree
      await loadFileTree(currentPath || undefined)

      // Open the new file
      if (currentPath) {
        onFileSelect(`${currentPath}/${newFileName}`, true)
      } else {
        onFileSelect(newFileName, false)
      }
    } catch (err) {
      console.error('Error creating file:', err)
      toast.error(err instanceof Error ? err.message : 'Failed to create file')
    } finally {
      setCreating(false)
    }
  }

  useEffect(() => {
    loadFileTree()

    // Listen for 'open-folder' event from CodeSidebar
    const handleOpenFolderEvent = () => {
      handleOpenFolder()
    }
    window.addEventListener('open-folder', handleOpenFolderEvent)

    // Auto-refresh every 500ms when a workspace is open (like VS Code)
    const refreshInterval = setInterval(() => {
      const storedPath = localStorage.getItem('ns.code.workspaceRoot')
      if (storedPath && !loading) {
        loadFileTree(storedPath)
      }
    }, 500)

    return () => {
      window.removeEventListener('open-folder', handleOpenFolderEvent)
      clearInterval(refreshInterval)
    }
  }, [])

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

  const handleFileClick = (path: string) => {
    if (currentPath) {
      // If browsing absolute path, send full path
      onFileSelect(`${currentPath}/${path}`, true)
    } else {
      onFileSelect(path, false)
    }
  }

  const renderNode = (node: FileNode, depth: number = 0): JSX.Element => {
    const isExpanded = expanded.has(node.path)
    const isSelected = selectedFile === node.path || selectedFile === `${currentPath}/${node.path}`
    const paddingLeft = depth * 16

    if (node.type === 'directory') {
      return (
        <div key={node.path}>
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
        key={node.path}
        onClick={() => handleFileClick(node.path)}
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
              onClick={() => loadFileTree(currentPath || undefined)}
              className="p-1 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-lg transition-colors"
              title="Refresh"
            >
              <RefreshCw className="w-3.5 h-3.5 text-gray-500" />
            </button>
          </div>
        </div>
        {currentPath && (
          <div className="text-xs text-gray-500 truncate" title={currentPath}>
            {currentPath}
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
                {currentPath ? `In ${currentPath}` : 'In workspace'}
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
