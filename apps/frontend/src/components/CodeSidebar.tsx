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
import { FolderOpen, MessageSquarePlus, FolderPlus, FilePlus, Trash2, Package, Folder, MessageCircle, Clock, Settings, Wand2 } from 'lucide-react'
import { authFetch } from '@/lib/api'
import { AgentSessionsPanel } from './AgentSessions/AgentSessionsPanel'

interface CodeSidebarProps {
  onFileSelect: (path: string, isAbsolute?: boolean) => void
  selectedFile: string | null
  onOpenLibrary: () => void
  onOpenSettings: () => void
}

export function CodeSidebar({ onFileSelect, selectedFile, onOpenLibrary, onOpenSettings }: CodeSidebarProps) {
  const [activeTab, setActiveTab] = useState<'files' | 'chat' | 'agent'>('files')
  const [chatView, setChatView] = useState<'history' | 'git'>('history') // Toggle between chat history and git view
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

    // Listen for workspace changes
    const handleWorkspaceChange = (event: CustomEvent) => {
      const path = event.detail?.path
      if (path) {
        const folderName = path.split('/').pop() || path
        setProjectName(sanitizeName(folderName))
      }
    }

    // Listen for open agent sessions event
    const handleOpenAgentSessions = () => {
      setActiveTab('agent')
    }

    window.addEventListener('workspace-changed', handleWorkspaceChange as EventListener)
    window.addEventListener('open-agent-sessions', handleOpenAgentSessions)

    return () => {
      window.removeEventListener('workspace-changed', handleWorkspaceChange as EventListener)
      window.removeEventListener('open-agent-sessions', handleOpenAgentSessions)
    }
  }, [])

  return (
    <div className="h-full flex flex-col">
      {/* Tab Headers */}
      <div className="flex border-b border-gray-200 dark:border-gray-800 relative">
        <button
          onClick={() => setActiveTab('files')}
          className={`
            flex-1 px-3 py-2 text-sm font-medium transition-colors
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
            flex-1 px-3 py-2 text-sm font-medium transition-colors
            ${activeTab === 'chat'
              ? 'text-primary-600 dark:text-primary-400 border-b-2 border-primary-600 dark:border-primary-400'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
            }
          `}
        >
          Chat
        </button>

        {/* Vertical divider */}
        <div className="w-px bg-gray-200 dark:bg-gray-700 my-2" />

        <button
          onClick={() => setActiveTab('agent')}
          className={`
            flex-1 px-3 py-2 text-sm font-medium transition-colors
            ${activeTab === 'agent'
              ? 'text-primary-600 dark:text-primary-400 border-b-2 border-primary-600 dark:border-primary-400'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
            }
          `}
        >
          Agent
        </button>
      </div>

      {/* Context-dependent action button */}
      {activeTab !== 'agent' && (
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
      )}

      {/* Icon Row - Tab-dependent buttons */}
      {activeTab !== 'agent' && (
        <div className="flex items-center justify-center gap-2 py-2 border-b border-gray-200 dark:border-gray-700">
          {activeTab === 'files' ? (
          <>
            {/* Code Tab: 4 buttons */}
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
          </>
        ) : (
          <>
            {/* Chat Tab: 4 buttons (Library, Chat History, Git, Settings) */}
            <button
              onClick={onOpenLibrary}
              className="p-2 hover:bg-white/60 dark:hover:bg-gray-700/60 rounded-lg transition-all text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400"
              title="Project Library"
            >
              <Folder size={18} />
            </button>
            <button
              onClick={() => setChatView('history')}
              className={`p-2 hover:bg-white/60 dark:hover:bg-gray-700/60 rounded-lg transition-all ${
                chatView === 'history'
                  ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400'
                  : 'text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400'
              }`}
              title="Chat History"
            >
              <MessageCircle size={18} />
            </button>
            <button
              onClick={() => setChatView('git')}
              className={`p-2 hover:bg-white/60 dark:hover:bg-gray-700/60 rounded-lg transition-all ${
                chatView === 'git'
                  ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400'
                  : 'text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400'
              }`}
              title="Git Repository"
            >
              <Clock size={18} />
            </button>
            <button
              onClick={onOpenSettings}
              className="p-2 hover:bg-white/60 dark:hover:bg-gray-700/60 rounded-lg transition-all text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400"
              title="Code Chat Settings"
            >
              <Settings size={18} />
            </button>
          </>
        )}
        </div>
      )}

      {/* Tab Content */}
      <div className="flex-1 overflow-hidden">
        <div className={activeTab === 'files' ? '' : 'hidden'}>
          <FileBrowser
            onFileSelect={onFileSelect}
            selectedFile={selectedFile}
          />
        </div>
        <div className={activeTab === 'chat' ? '' : 'hidden'}>
          <div className={chatView === 'history' ? '' : 'hidden'}>
            <ChatHistory />
          </div>
          <div className={chatView === 'git' ? '' : 'hidden'}>
            <GitRepository />
          </div>
        </div>
        <div className={activeTab === 'agent' ? '' : 'hidden'}>
          <AgentSessionsPanel />
        </div>
      </div>
    </div>
  )
}

// Chat History Component (Placeholder)
function ChatHistory() {
  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 overflow-auto p-4">
        <div className="text-center text-sm text-gray-500 py-8">
          <div className="w-12 h-12 mx-auto mb-3 flex items-center justify-center">
            <MessageCircle size={43} strokeWidth={1.5} className="opacity-50" />
          </div>
          <p>No chat history yet</p>
          <p className="text-xs mt-1">Start a conversation in the chat panel</p>
        </div>
      </div>
    </div>
  )
}

// Git Repository Component
function GitRepository() {
  const [commits, setCommits] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [branch, setBranch] = useState<string>('main')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadGitCommits()

    // Listen for workspace changes to reload commits
    const handleWorkspaceChange = () => {
      loadGitCommits()
    }
    window.addEventListener('workspace-changed', handleWorkspaceChange)

    return () => {
      window.removeEventListener('workspace-changed', handleWorkspaceChange)
    }
  }, [])

  const loadGitCommits = async () => {
    try {
      setLoading(true)
      setError(null)

      const res = await authFetch('/api/v1/code/git/log')
      const data = await res.json()

      if (data.error) {
        setError(data.error)
        setCommits([])
        setBranch('main')
      } else {
        setCommits(data.commits || [])
        setBranch(data.branch || 'main')
      }

      setLoading(false)
    } catch (error) {
      console.error('Error loading git commits:', error)
      setError('Failed to load git commits')
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto mb-3"></div>
          <p className="text-sm text-gray-500">Loading commits...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Commit List */}
      <div className="flex-1 overflow-auto p-4">
        {commits.length === 0 ? (
          <div className="text-center text-sm text-gray-500 py-8">
            <div className="w-12 h-12 mx-auto mb-3 flex items-center justify-center">
              <Clock size={39} strokeWidth={1.5} className="opacity-50" />
            </div>
            {error === 'No workspace opened' ? (
              <>
                <p>No workspace opened</p>
                <p className="text-xs mt-1">Open a project folder to view git history</p>
              </>
            ) : error === 'Not a git repository' ? (
              <>
                <p>Not a git repository</p>
                <p className="text-xs mt-1">Initialize git in your project folder</p>
              </>
            ) : (
              <>
                <p>No commits yet</p>
                <p className="text-xs mt-1">Make your first commit</p>
              </>
            )}
          </div>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {commits.map((commit) => (
              <div
                key={commit.hash}
                className="p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors cursor-pointer group"
              >
                {/* Commit Message */}
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 w-2 h-2 mt-2 rounded-full bg-primary-600"></div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate group-hover:text-primary-600 dark:group-hover:text-primary-400">
                      {commit.message}
                    </p>
                    <div className="flex items-center gap-2 mt-1.5 text-xs text-gray-500 dark:text-gray-400">
                      <span className="font-mono bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded">
                        {commit.short_hash || commit.hash.substring(0, 8)}
                      </span>
                      <span>•</span>
                      <span>{commit.author}</span>
                      <span>•</span>
                      <span>{commit.date}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
