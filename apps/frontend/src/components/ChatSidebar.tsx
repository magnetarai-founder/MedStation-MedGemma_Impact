import { useEffect } from 'react'
import { MessageSquarePlus, MessageSquare, Trash2 } from 'lucide-react'
import { useChatStore } from '../stores/chatStore'
import { api } from '../lib/api'

export function ChatSidebar() {
  const {
    sessions,
    activeChatId,
    setSessions,
    setActiveChat,
    setMessages
  } = useChatStore()

  // Load sessions on mount
  useEffect(() => {
    loadSessions()
  }, [])

  const loadSessions = async () => {
    try {
      const response = await fetch(`/api/v1/chat/sessions`)
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
      const response = await fetch(`/api/v1/chat/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: 'New Chat',
          model: 'qwen2.5-coder:7b-instruct'
        })
      })

      if (response.ok) {
        const newSession = await response.json()
        setSessions([newSession, ...sessions])
        selectChat(newSession.id)
      }
    } catch (error) {
      console.error('Failed to create chat:', error)
    }
  }

  const selectChat = async (chatId: string) => {
    setActiveChat(chatId)

    // Load messages for this chat
    try {
      const response = await fetch(`/api/v1/chat/sessions/${chatId}`)
      if (response.ok) {
        const data = await response.json()
        setMessages(data.messages || [])
      }
    } catch (error) {
      console.error('Failed to load messages:', error)
    }
  }

  const deleteChat = async (chatId: string, e: React.MouseEvent) => {
    e.stopPropagation()

    if (!confirm('Delete this chat?')) return

    try {
      const response = await fetch(`/api/v1/chat/sessions/${chatId}`, {
        method: 'DELETE'
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
        <button
          onClick={createNewChat}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm bg-primary-600 hover:bg-primary-700 text-white rounded-lg hover:shadow-md transition-all"
        >
          <MessageSquarePlus size={16} />
          <span>New Chat</span>
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
            {sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => selectChat(session.id)}
                className={`w-full text-left p-3 rounded-2xl mb-2 group transition-all ${
                  activeChatId === session.id
                    ? 'bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-700 shadow-sm'
                    : 'hover:bg-white/50 dark:hover:bg-gray-700/50 border border-transparent'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <MessageSquare size={14} className="text-gray-400 flex-shrink-0" />
                      <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                        {session.title}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                      <span>{session.message_count} messages</span>
                      <span>•</span>
                      <span>{formatDate(session.updated_at)}</span>
                    </div>
                  </div>

                  <button
                    onClick={(e) => deleteChat(session.id, e)}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-opacity"
                    title="Delete chat"
                  >
                    <Trash2 size={14} className="text-red-600 dark:text-red-400" />
                  </button>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

    </div>
  )
}
