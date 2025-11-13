import { useEffect, useState } from 'react'
import { MessageSquarePlus, MessageSquare, Trash2, Edit2, Archive, ArchiveRestore, Check, X } from 'lucide-react'
import { useChatStore } from '../stores/chatStore'
import { api } from '../lib/api'
import { ContextBadge } from './ContextBadge'
import { showToast } from '../lib/toast'

export function ChatSidebar() {
  const {
    sessions,
    activeChatId,
    setSessions,
    setActiveChat,
    setMessages
  } = useChatStore()

  const [editingSessionId, setEditingSessionId] = useState<string | null>(null)
  const [editingTitle, setEditingTitle] = useState('')
  const [showArchived, setShowArchived] = useState(false)

  // Load sessions on mount
  useEffect(() => {
    loadSessions()
  }, [])

  const loadSessions = async () => {
    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch(`/api/v1/chat/sessions`, {
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
          'Content-Type': 'application/json'
        }
      })
      if (response.ok) {
        const data = await response.json()
        setSessions(data)

        // If there's a stored active chat ID (from current session), try to restore it
        if (activeChatId) {
          const storedChatExists = data.find((s: any) => s.id === activeChatId)
          if (storedChatExists) {
            selectChat(activeChatId)
          } else {
            // Stored chat doesn't exist anymore, clear it
            setActiveChat(null)
          }
        }

        // Don't auto-create or auto-select - let user choose
      }
    } catch (error) {
      console.error('Failed to load chat sessions:', error)
    }
  }

  const createNewChat = async () => {
    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch(`/api/v1/chat/sessions`, {
        method: 'POST',
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          title: 'New Chat',
          model: 'qwen2.5-coder:7b-instruct'
        })
      })

      if (response.ok) {
        const newSession = await response.json()
        setSessions([newSession, ...sessions])
        selectChat(newSession.id)
      } else {
        console.error('Failed to create chat:', response.status, response.statusText)
      }
    } catch (error) {
      console.error('Failed to create chat:', error)
    }
  }

  const selectChat = async (chatId: string) => {
    setActiveChat(chatId)

    // Load messages for this chat
    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch(`/api/v1/chat/sessions/${chatId}`, {
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
          'Content-Type': 'application/json'
        }
      })
      if (response.ok) {
        const data = await response.json()
        setMessages(data.messages || [])
      }
    } catch (error) {
      console.error('Failed to load messages:', error)
    }
  }

  const startRename = (session: any, e: React.MouseEvent) => {
    e.stopPropagation()
    setEditingSessionId(session.id)
    setEditingTitle(session.title)
  }

  const cancelRename = (e: React.MouseEvent) => {
    e.stopPropagation()
    setEditingSessionId(null)
    setEditingTitle('')
  }

  const saveRename = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation()

    if (!editingTitle.trim()) {
      showToast.error('Title cannot be empty')
      return
    }

    const previousTitle = sessions.find(s => s.id === sessionId)?.title

    // Optimistic update
    setSessions(sessions.map(s =>
      s.id === sessionId ? { ...s, title: editingTitle } : s
    ))
    setEditingSessionId(null)

    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch(`/api/v1/chat/sessions/${sessionId}/rename`, {
        method: 'PATCH',
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ title: editingTitle })
      })

      if (!response.ok) {
        // Revert on failure
        setSessions(sessions.map(s =>
          s.id === sessionId ? { ...s, title: previousTitle } : s
        ))
        showToast.error('Failed to rename session')
      }
    } catch (error) {
      // Revert on error
      setSessions(sessions.map(s =>
        s.id === sessionId ? { ...s, title: previousTitle } : s
      ))
      showToast.error('Network error - rename failed')
    }
  }

  const toggleArchive = async (session: any, e: React.MouseEvent) => {
    e.stopPropagation()

    const newArchivedStatus = !session.archived

    // Optimistic update
    setSessions(sessions.map(s =>
      s.id === session.id ? { ...s, archived: newArchivedStatus } : s
    ))

    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch(`/api/v1/chat/sessions/${session.id}/archive`, {
        method: 'PATCH',
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ archived: newArchivedStatus })
      })

      if (!response.ok) {
        // Revert on failure
        setSessions(sessions.map(s =>
          s.id === session.id ? { ...s, archived: !newArchivedStatus } : s
        ))
        showToast.error('Failed to archive session')
      } else {
        showToast.success(newArchivedStatus ? 'Session archived' : 'Session restored')
      }
    } catch (error) {
      // Revert on error
      setSessions(sessions.map(s =>
        s.id === session.id ? { ...s, archived: !newArchivedStatus } : s
      ))
      showToast.error('Network error - archive failed')
    }
  }

  const deleteChat = async (chatId: string, e: React.MouseEvent) => {
    e.stopPropagation()

    if (!confirm('Delete this chat?')) return

    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch(`/api/v1/chat/sessions/${chatId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        const updatedSessions = sessions.filter(s => s.id !== chatId)
        setSessions(updatedSessions)

        // If deleted active chat, select another
        if (activeChatId === chatId) {
          if (updatedSessions.length > 0) {
            selectChat(updatedSessions[0].id)
          } else {
            setActiveChat(null)
            setMessages([])
          }
        }
      }
    } catch (error) {
      console.error('Failed to delete chat:', error)
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays}d ago`

    return date.toLocaleDateString()
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-white/10 dark:border-gray-700/30">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Chats</h2>
          <ContextBadge size="xs" />
        </div>
        <button
          onClick={createNewChat}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm bg-primary-600 hover:bg-primary-700 text-white rounded-lg hover:shadow-md transition-all mb-2"
        >
          <MessageSquarePlus size={16} />
          <span>New Chat</span>
        </button>
        <button
          onClick={() => setShowArchived(!showArchived)}
          className="w-full flex items-center justify-center gap-2 px-2 py-1.5 text-xs text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-all"
        >
          {showArchived ? <ArchiveRestore size={14} /> : <Archive size={14} />}
          <span>{showArchived ? 'Hide Archived' : 'Show Archived'}</span>
        </button>
      </div>

      {/* Chat List */}
      <div className="flex-1 overflow-y-auto">
        {sessions.length === 0 ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">
            <MessageSquare size={48} className="mx-auto mb-4 opacity-50" />
            <p className="text-sm">No chats yet</p>
            <p className="text-xs mt-2">Create a new chat to get started</p>
          </div>
        ) : (
          <div className="p-2">
            {sessions
              .filter(session => showArchived || !session.archived)
              .map((session) => (
              <div
                key={session.id}
                className={`w-full text-left p-3 rounded-2xl mb-2 group transition-all ${
                  activeChatId === session.id
                    ? 'bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-700 shadow-sm'
                    : 'hover:bg-white/50 dark:hover:bg-gray-700/50 border border-transparent'
                } ${session.archived ? 'opacity-60' : ''}`}
                onClick={() => !editingSessionId && selectChat(session.id)}
                role="button"
                tabIndex={0}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <MessageSquare size={14} className="text-gray-400 flex-shrink-0" />
                      {editingSessionId === session.id ? (
                        <div className="flex-1 flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="text"
                            value={editingTitle}
                            onChange={(e) => setEditingTitle(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') saveRename(session.id, e as any)
                              if (e.key === 'Escape') cancelRename(e as any)
                            }}
                            className="flex-1 px-2 py-0.5 text-sm bg-white dark:bg-gray-800 border border-primary-300 dark:border-primary-600 rounded focus:outline-none focus:ring-1 focus:ring-primary-500"
                            autoFocus
                          />
                          <button
                            onClick={(e) => saveRename(session.id, e)}
                            className="p-0.5 hover:bg-green-100 dark:hover:bg-green-900/20 rounded"
                            title="Save"
                          >
                            <Check size={14} className="text-green-600 dark:text-green-400" />
                          </button>
                          <button
                            onClick={cancelRename}
                            className="p-0.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
                            title="Cancel"
                          >
                            <X size={14} className="text-gray-600 dark:text-gray-400" />
                          </button>
                        </div>
                      ) : (
                        <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                          {session.title}
                          {session.archived && <span className="ml-2 text-xs text-gray-500">(Archived)</span>}
                        </span>
                      )}
                    </div>
                    {editingSessionId !== session.id && (
                      <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                        <span>{session.message_count} messages</span>
                        <span>•</span>
                        <span>{formatDate(session.updated_at)}</span>
                      </div>
                    )}
                  </div>

                  {editingSessionId !== session.id && (
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={(e) => startRename(session, e)}
                        className="p-1 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded"
                        title="Rename"
                      >
                        <Edit2 size={14} className="text-blue-600 dark:text-blue-400" />
                      </button>
                      <button
                        onClick={(e) => toggleArchive(session, e)}
                        className="p-1 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded"
                        title={session.archived ? "Restore" : "Archive"}
                      >
                        {session.archived ? (
                          <ArchiveRestore size={14} className="text-amber-600 dark:text-amber-400" />
                        ) : (
                          <Archive size={14} className="text-amber-600 dark:text-amber-400" />
                        )}
                      </button>
                      <button
                        onClick={(e) => deleteChat(session.id, e)}
                        className="p-1 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                        title="Delete"
                      >
                        <Trash2 size={14} className="text-red-600 dark:text-red-400" />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

    </div>
  )
}
