/**
 * CodeSidebar - EXACT CARBON COPY of Database Tab left sidebar structure
 *
 * Structure matching Database Tab (App.tsx lines 250-284):
 * - File browser at top
 * - Icon row for actions (placeholder for future features)
 * - Tabs for navigation (Files/Logs similar to Columns/Logs)
 */

import { useState, useEffect } from 'react'
import { FileBrowser } from './FileBrowser'
import { FolderOpen, MessageSquarePlus, FolderPlus, FilePlus, Trash2, Package } from 'lucide-react'

interface CodeSidebarProps {
  onFileSelect: (path: string, isAbsolute?: boolean) => void
  selectedFile: string | null
}

export function CodeSidebar({ onFileSelect, selectedFile }: CodeSidebarProps) {
  const [activeTab, setActiveTab] = useState<'files' | 'chat'>('files')
  const [projectName, setProjectName] = useState<string | null>(null)

  const sanitizeName = (name: string): string => {
    // Same logic as _sanitize_column_name in data_engine.py
    // Replace special chars with underscores
    let sanitized = name.replace(/[^\w\s]/g, '_')
    // Replace spaces with underscores
    sanitized = sanitized.replace(/\s+/g, '_')
    // Remove leading/trailing underscores
    sanitized = sanitized.replace(/^_+|_+$/g, '')
    // Ensure it doesn't start with a number
    if (sanitized && /^\d/.test(sanitized)) {
      sanitized = `project_${sanitized}`
    }
    return sanitized || 'unnamed'
  }

  const handleOpenFolder = () => {
    // Get stored workspace root and sanitize it for display
    const storedPath = localStorage.getItem('ns.code.workspaceRoot')
    if (storedPath) {
      const folderName = storedPath.split('/').pop() || storedPath
      setProjectName(sanitizeName(folderName))
    }
    // This will be handled by FileBrowser component
    window.dispatchEvent(new Event('open-folder'))
  }

  const handleNewChat = () => {
    // TODO: Create new chat session
    console.log('New chat clicked')
  }

  // Load project name on mount if workspace root is already set
  useEffect(() => {
    const storedPath = localStorage.getItem('ns.code.workspaceRoot')
    if (storedPath) {
      const folderName = storedPath.split('/').pop() || storedPath
      setProjectName(sanitizeName(folderName))
    }
  }, [])

  return (
    <div className="h-full flex flex-col">
      {/* Tab Headers */}
      <div className="flex border-b border-gray-200 dark:border-gray-800 relative">
        <button
          onClick={() => setActiveTab('files')}
          className={`
            flex-1 px-4 py-2 text-sm font-medium transition-colors
            ${activeTab === 'files'
              ? 'text-primary-600 dark:text-primary-400 border-b-2 border-primary-600 dark:border-primary-400'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
            }
          `}
        >
          Code
        </button>

        {/* Vertical divider */}
        <div className="w-px bg-gray-200 dark:bg-gray-700 my-2" />

        <button
          onClick={() => setActiveTab('chat')}
          className={`
            flex-1 px-4 py-2 text-sm font-medium transition-colors
            ${activeTab === 'chat'
              ? 'text-primary-600 dark:text-primary-400 border-b-2 border-primary-600 dark:border-primary-400'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
            }
          `}
        >
          Chat
        </button>
      </div>

      {/* Context-dependent action button */}
      <div className="flex items-center justify-center gap-2 py-2 border-b border-gray-200 dark:border-gray-700">
        {activeTab === 'files' ? (
          <button
            onClick={handleOpenFolder}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium hover:bg-white/60 dark:hover:bg-gray-700/60 rounded-lg transition-all text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400 truncate max-w-full"
            title={projectName ? `Project: ${projectName}` : "Open Project or Folder"}
          >
            <FolderOpen size={16} className="flex-shrink-0" />
            <span className="truncate">
              {projectName || 'Open Project or Folder'}
            </span>
          </button>
        ) : (
          <button
            onClick={handleNewChat}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium hover:bg-white/60 dark:hover:bg-gray-700/60 rounded-lg transition-all text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400"
            title="New Chat"
          >
            <MessageSquarePlus size={16} />
            <span>New Chat</span>
          </button>
        )}
      </div>

      {/* Icon Row - Create Project, Folder, File, Delete */}
      <div className="flex items-center justify-center gap-2 py-2 border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => console.log('Create project clicked')}
          className="p-2 hover:bg-white/60 dark:hover:bg-gray-700/60 rounded-lg transition-all text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400"
          title="Create Project"
        >
          <Package size={18} />
        </button>
        <button
          onClick={() => console.log('Create folder clicked')}
          className="p-2 hover:bg-white/60 dark:hover:bg-gray-700/60 rounded-lg transition-all text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400"
          title="Create Folder"
        >
          <FolderPlus size={18} />
        </button>
        <button
          onClick={() => console.log('Create file clicked')}
          className="p-2 hover:bg-white/60 dark:hover:bg-gray-700/60 rounded-lg transition-all text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400"
          title="Create File"
        >
          <FilePlus size={18} />
        </button>
        <button
          onClick={() => console.log('Delete clicked')}
          className="p-2 hover:bg-white/60 dark:hover:bg-gray-700/60 rounded-lg transition-all text-gray-600 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400"
          title="Delete"
        >
          <Trash2 size={18} />
        </button>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'files' && (
          <FileBrowser
            onFileSelect={onFileSelect}
            selectedFile={selectedFile}
          />
        )}
        {activeTab === 'chat' && (
          <div className="p-4 text-center text-sm text-gray-500">
            Chat interface will appear here
          </div>
        )}
      </div>
    </div>
  )
}
