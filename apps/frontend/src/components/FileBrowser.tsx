/**
 * FileBrowser - File tree navigation for Code Tab
 * Uses patterns from Continue's file tree implementation
 */

import { useState, useEffect } from 'react'
import { Folder, File, ChevronRight, ChevronDown, RefreshCw } from 'lucide-react'

interface FileNode {
  name: string
  type: 'file' | 'directory'
  path: string
  size?: number
  children?: FileNode[]
}

interface FileBrowserProps {
  onFileSelect: (path: string) => void
  selectedFile: string | null
}

export function FileBrowser({ onFileSelect, selectedFile }: FileBrowserProps) {
  const [tree, setTree] = useState<FileNode[]>([])
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadFileTree = async () => {
    setLoading(true)
    setError(null)

    try {
      const res = await fetch('/api/v1/code/files?recursive=true')

      if (!res.ok) {
        throw new Error('Failed to load file tree')
      }

      const data = await res.json()
      setTree(data.items || [])
    } catch (err) {
      console.error('Error loading file tree:', err)
      setError(err instanceof Error ? err.message : 'Failed to load files')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadFileTree()
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

  const renderNode = (node: FileNode, depth: number = 0): JSX.Element => {
    const isExpanded = expanded.has(node.path)
    const isSelected = selectedFile === node.path
    const paddingLeft = depth * 16

    if (node.type === 'directory') {
      return (
        <div key={node.path}>
          <button
            onClick={() => toggleExpand(node.path)}
            className={`flex items-center gap-2 py-1.5 px-2 hover:bg-gray-100 dark:hover:bg-gray-700/50 w-full text-left transition-colors ${
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
        onClick={() => onFileSelect(node.path)}
        className={`flex items-center gap-2 py-1.5 px-2 hover:bg-gray-100 dark:hover:bg-gray-700/50 w-full text-left transition-colors ${
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
          onClick={loadFileTree}
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
      <div className="p-8 text-center space-y-3">
        <Folder className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-600" />
        <div className="space-y-1">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
            No files yet
          </p>
          <p className="text-xs text-gray-500">
            Your code workspace is empty
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full overflow-auto">
      {/* Header */}
      <div className="sticky top-0 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-3 py-2 flex items-center justify-between">
        <span className="text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wide">
          Files
        </span>
        <button
          onClick={loadFileTree}
          className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
          title="Refresh"
        >
          <RefreshCw className="w-3.5 h-3.5 text-gray-500" />
        </button>
      </div>

      {/* File tree */}
      <div className="py-1">
        {tree.map(node => renderNode(node))}
      </div>
    </div>
  )
}
