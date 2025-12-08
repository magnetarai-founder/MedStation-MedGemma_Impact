import { useState } from 'react'
import { Folder, FolderOpen, FileText, MoreVertical, FolderPlus, Filter, ArrowRight } from 'lucide-react'
import { useQueriesStore, QueryNode } from '@/stores/queriesStore'
import { useNavigationStore } from '@/stores/navigationStore'
import { useEditorStore } from '@/stores/editorStore'

export function SavedQueriesTree() {
  const { queries, addQuery, addFolder, deleteNode, updateQuery } = useQueriesStore()
  const { setActiveTab } = useNavigationStore()
  const { loadQuery } = useEditorStore()
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set())
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; nodeId: string } | null>(null)
  const [renamingId, setRenamingId] = useState<string | null>(null)
  const [renamingValue, setRenamingValue] = useState('')
  const [filterType, setFilterType] = useState<'all' | 'sql' | 'json'>('all')

  const toggleFolder = (id: string) => {
    setExpandedFolders(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const handleQueryClick = (node: QueryNode) => {
    if (node.type !== 'query' || !node.query) {
      console.log('Cannot load query - invalid node or empty query', node)
      return
    }

    console.log('Loading query into editor:', {
      name: node.name,
      type: node.queryType,
      queryLength: node.query.length
    })

    // Load query into editor using the store
    loadQuery(node.query, node.queryType)

    // Switch to main tab
    setActiveTab('editor')
  }

  const handleContextMenu = (e: React.MouseEvent, nodeId: string) => {
    e.preventDefault()
    e.stopPropagation()
    setContextMenu({ x: e.clientX, y: e.clientY, nodeId })
  }

  const handleRename = (node: QueryNode) => {
    setRenamingId(node.id)
    setRenamingValue(node.name)
    setContextMenu(null)
  }

  const handleRenameSubmit = (id: string) => {
    if (renamingValue.trim()) {
      updateQuery(id, { name: renamingValue.trim() })
    }
    setRenamingId(null)
    setRenamingValue('')
  }

  const handleDelete = (id: string) => {
    if (window.confirm('Delete this item and all its contents?')) {
      deleteNode(id)
    }
    setContextMenu(null)
  }

  const handleNewFolder = (parentId?: string) => {
    const name = prompt('Folder name:')
    if (name?.trim()) {
      addFolder(name.trim(), parentId || null)
    }
    setContextMenu(null)
  }

  const renderNode = (node: QueryNode, depth: number = 0) => {
    const isExpanded = expandedFolders.has(node.id)
    const isRenaming = renamingId === node.id

    if (node.type === 'folder') {
      return (
        <div key={node.id}>
          <div
            style={{ paddingLeft: `${depth * 16}px` }}
            className="flex items-center space-x-2 px-2 py-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 cursor-pointer group"
            onClick={() => toggleFolder(node.id)}
            onContextMenu={(e) => handleContextMenu(e, node.id)}
          >
            {isExpanded ? <FolderOpen className="w-4 h-4 text-primary-500" /> : <Folder className="w-4 h-4 text-gray-500" />}
            {isRenaming ? (
              <input
                type="text"
                value={renamingValue}
                onChange={(e) => setRenamingValue(e.target.value)}
                onBlur={() => handleRenameSubmit(node.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleRenameSubmit(node.id)
                  if (e.key === 'Escape') setRenamingId(null)
                }}
                onClick={(e) => e.stopPropagation()}
                autoFocus
                className="flex-1 px-1 text-sm bg-white dark:bg-gray-900 border border-primary-500 rounded"
              />
            ) : (
              <span className="flex-1 text-sm truncate">{node.name}</span>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation()
                handleContextMenu(e, node.id)
              }}
              className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
            >
              <MoreVertical className="w-3 h-3" />
            </button>
          </div>
          {isExpanded && node.children?.map(child => renderNode(child, depth + 1))}
        </div>
      )
    }

    // Query node
    return (
      <div
        key={node.id}
        style={{ paddingLeft: `${depth * 16}px` }}
        className="flex items-center space-x-2 px-2 py-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 group"
        onContextMenu={(e) => handleContextMenu(e, node.id)}
      >
        <FileText className="w-4 h-4 text-blue-500" />
        {isRenaming ? (
          <input
            type="text"
            value={renamingValue}
            onChange={(e) => setRenamingValue(e.target.value)}
            onBlur={() => handleRenameSubmit(node.id)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleRenameSubmit(node.id)
              if (e.key === 'Escape') setRenamingId(null)
            }}
            onClick={(e) => e.stopPropagation()}
            autoFocus
            className="flex-1 px-1 text-sm bg-white dark:bg-gray-900 border border-primary-500 rounded"
          />
        ) : (
          <span className="flex-1 text-sm truncate">{node.name}</span>
        )}
        <span className="text-xs text-gray-400 uppercase">{node.queryType}</span>
        <button
          onClick={(e) => {
            e.stopPropagation()
            handleQueryClick(node)
          }}
          className="p-1.5 bg-primary-500 hover:bg-primary-600 text-white rounded transition-colors"
          title="Load into editor"
        >
          <ArrowRight className="w-4 h-4" />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation()
            handleContextMenu(e, node.id)
          }}
          className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
        >
          <MoreVertical className="w-3 h-3" />
        </button>
      </div>
    )
  }

  const filterNodes = (nodes: QueryNode[]): QueryNode[] => {
    return nodes
      .map(node => {
        if (node.type === 'folder') {
          const filteredChildren = filterNodes(node.children || [])
          // Keep folder if it has matching children or if filter is 'all'
          if (filterType === 'all' || filteredChildren.length > 0) {
            return { ...node, children: filteredChildren }
          }
          return null
        }
        // Query node - filter by type
        if (filterType === 'all' || node.queryType === filterType) {
          return node
        }
        return null
      })
      .filter(Boolean) as QueryNode[]
  }

  const filteredQueries = filterNodes(queries)

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-800">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold">Library</h3>
          <div className="flex space-x-1">
            <button
              onClick={() => handleNewFolder()}
              className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
              title="New Folder"
            >
              <FolderPlus className="w-4 h-4" />
            </button>
          </div>
        </div>
        {/* Filter */}
        <div className="flex items-center space-x-2">
          <Filter className="w-3 h-3 text-gray-400" />
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value as any)}
            className="flex-1 text-xs px-2 py-1 rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900"
          >
            <option value="all">All Types</option>
            <option value="sql">SQL</option>
            <option value="json">JSON</option>
          </select>
        </div>
      </div>

      {/* Tree */}
      <div className="flex-1 overflow-auto">
        {queries.length === 0 ? (
          <div className="p-4 text-center text-sm text-gray-500">
            No saved files yet
          </div>
        ) : filteredQueries.length === 0 ? (
          <div className="p-4 text-center text-sm text-gray-500">
            No files match filter
          </div>
        ) : (
          filteredQueries.map(node => renderNode(node))
        )}
      </div>

      {/* Context Menu */}
      {contextMenu && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setContextMenu(null)}
          />
          <div
            className="fixed z-50 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg py-1 min-w-[150px]"
            style={{ left: contextMenu.x, top: contextMenu.y }}
          >
            <button
              onClick={() => {
                const node = useQueriesStore.getState().findNodeById(contextMenu.nodeId)
                if (node) handleRename(node)
              }}
              className="w-full px-3 py-1.5 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              Rename
            </button>
            {useQueriesStore.getState().findNodeById(contextMenu.nodeId)?.type === 'folder' && (
              <button
                onClick={() => handleNewFolder(contextMenu.nodeId)}
                className="w-full px-3 py-1.5 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                New Subfolder
              </button>
            )}
            <button
              onClick={() => handleDelete(contextMenu.nodeId)}
              className="w-full px-3 py-1.5 text-left text-sm text-red-600 hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              Delete
            </button>
          </div>
        </>
      )}
    </div>
  )
}
