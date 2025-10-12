import { useEffect, useState, useRef } from 'react'
import { Send, Smile, Paperclip, Hash, Bold, Italic, Code, Link as LinkIcon, AtSign } from 'lucide-react'
import { useTeamChatStore } from '../stores/teamChatStore'

interface TeamChatWindowProps {
  mode: 'solo' | 'p2p'
}

interface LocalMessage {
  id: string
  channel_id: string
  sender_name: string
  content: string
  timestamp: string
  type: 'text' | 'file'
}

export function TeamChatWindow({ mode }: TeamChatWindowProps) {
  const {
    channels,
    activeChannelId,
  } = useTeamChatStore()

  const [messageInput, setMessageInput] = useState('')
  const [messages, setMessages] = useState<LocalMessage[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const activeChannel = channels.find(ch => ch.id === activeChannelId)

  // Load messages from localStorage in solo mode
  useEffect(() => {
    if (mode === 'solo' && activeChannelId) {
      const saved = localStorage.getItem(`solo_messages_${activeChannelId}`)
      if (saved) {
        setMessages(JSON.parse(saved))
      } else {
        setMessages([])
      }
    }
  }, [activeChannelId, mode])

  // Save messages when they change in solo mode
  useEffect(() => {
    if (mode === 'solo' && activeChannelId && messages.length > 0) {
      localStorage.setItem(`solo_messages_${activeChannelId}`, JSON.stringify(messages))
    }
  }, [messages, activeChannelId, mode])

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSendMessage = () => {
    if (!messageInput.trim() || !activeChannelId) return

    const newMessage: LocalMessage = {
      id: `msg_${Date.now()}`,
      channel_id: activeChannelId,
      sender_name: mode === 'solo' ? 'You' : 'Me',
      content: messageInput.trim(),
      timestamp: new Date().toISOString(),
      type: 'text'
    }

    setMessages([...messages, newMessage])
    setMessageInput('')
    inputRef.current?.focus()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const isToday = date.toDateString() === now.toDateString()

    if (isToday) {
      return date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
      })
    }

    const yesterday = new Date(now)
    yesterday.setDate(yesterday.getDate() - 1)
    if (date.toDateString() === yesterday.toDateString()) {
      return `Yesterday at ${date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
      })}`
    }

    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    })
  }

  if (!activeChannelId) {
    return (
      <div className="h-full flex items-center justify-center bg-white dark:bg-gray-950">
        <div className="text-center max-w-md">
          <div className="w-20 h-20 bg-gray-100 dark:bg-gray-900 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Hash size={40} className="text-gray-400 dark:text-gray-600" />
          </div>
          <h3 className="text-xl font-semibold text-gray-700 dark:text-gray-300 mb-2">
            {mode === 'solo' ? 'Your Personal Workspace' : 'Team Collaboration'}
          </h3>
          <p className="text-gray-500 dark:text-gray-400">
            {mode === 'solo'
              ? 'Select a channel to start taking notes and saving references'
              : 'Select a channel or start a direct message to begin chatting'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-950">
      {/* Channel Header (Slack-style) */}
      <div className="flex-shrink-0 px-4 py-3 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100 flex items-center gap-1">
              <Hash size={18} />
              {activeChannel?.name}
            </h2>
          </div>
          <div className="flex items-center gap-2">
            {/* Slack-style header icons */}
            <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-900 rounded transition-colors" title="Details">
              <svg width="18" height="18" fill="currentColor" className="text-gray-600 dark:text-gray-400" viewBox="0 0 20 20">
                <path d="M10 3a1.5 1.5 0 110 3 1.5 1.5 0 010-3zm0 5a1.5 1.5 0 110 3 1.5 1.5 0 010-3zm0 5a1.5 1.5 0 110 3 1.5 1.5 0 010-3z"/>
              </svg>
            </button>
          </div>
        </div>
        {activeChannel?.description && (
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            {activeChannel.description}
          </p>
        )}
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center max-w-md">
              <div className="w-16 h-16 bg-gray-100 dark:bg-gray-900 rounded-xl flex items-center justify-center mx-auto mb-3">
                <Hash size={32} className="text-gray-400 dark:text-gray-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                This is the beginning of #{activeChannel?.name}
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                {mode === 'solo'
                  ? 'Start saving notes, file references, and important information here.'
                  : 'This channel is where conversations about this topic happen.'}
              </p>
              <button
                onClick={() => inputRef.current?.focus()}
                className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors"
              >
                Send a message
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message, index) => {
              const showAvatar = index === 0 || messages[index - 1].sender_name !== message.sender_name

              return (
                <div
                  key={message.id}
                  className={`group flex gap-3 hover:bg-gray-50 dark:hover:bg-gray-900/30 -mx-2 px-2 py-1.5 rounded transition-colors ${
                    showAvatar ? 'mt-3' : 'mt-0.5'
                  }`}
                >
                  <div className="flex-shrink-0 w-9">
                    {showAvatar && (
                      <div className="w-9 h-9 rounded bg-gradient-to-br from-purple-500 to-purple-700 flex items-center justify-center text-white font-semibold text-sm">
                        {message.sender_name[0].toUpperCase()}
                      </div>
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    {showAvatar && (
                      <div className="flex items-baseline gap-2 mb-0.5">
                        <span className="font-bold text-gray-900 dark:text-gray-100 text-sm">
                          {message.sender_name}
                        </span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {formatTimestamp(message.timestamp)}
                        </span>
                      </div>
                    )}

                    <div className="text-gray-900 dark:text-gray-100 text-[15px] leading-relaxed">
                      {message.content}
                    </div>
                  </div>

                  {/* Message hover actions (Slack-style) */}
                  <div className="opacity-0 group-hover:opacity-100 flex items-start gap-0.5 transition-opacity">
                    <button className="p-1 hover:bg-gray-200 dark:hover:bg-gray-800 rounded text-gray-600 dark:text-gray-400" title="Add reaction">
                      <Smile size={16} />
                    </button>
                  </div>
                </div>
              )
            })}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Message Input (Slack-style) */}
      <div className="flex-shrink-0 px-4 pb-6">
        <div className="border-2 border-gray-300 dark:border-gray-700 rounded-lg focus-within:border-gray-400 dark:focus-within:border-gray-600 transition-colors">
          {/* Formatting toolbar */}
          <div className="flex items-center gap-1 px-2 py-1.5 border-b border-gray-200 dark:border-gray-800">
            <button className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 rounded text-gray-600 dark:text-gray-400 transition-colors" title="Bold">
              <Bold size={16} />
            </button>
            <button className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 rounded text-gray-600 dark:text-gray-400 transition-colors" title="Italic">
              <Italic size={16} />
            </button>
            <button className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 rounded text-gray-600 dark:text-gray-400 transition-colors" title="Code">
              <Code size={16} />
            </button>
            <button className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 rounded text-gray-600 dark:text-gray-400 transition-colors" title="Link">
              <LinkIcon size={16} />
            </button>
            <div className="flex-1"></div>
            <button className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 rounded text-gray-600 dark:text-gray-400 transition-colors" title="Emoji">
              <Smile size={16} />
            </button>
            <button className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 rounded text-gray-600 dark:text-gray-400 transition-colors" title="Attach file">
              <Paperclip size={16} />
            </button>
          </div>

          {/* Input area */}
          <div className="relative">
            <textarea
              ref={inputRef}
              value={messageInput}
              onChange={(e) => setMessageInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Message #${activeChannel?.name}`}
              className="w-full px-3 py-2.5 bg-transparent text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none resize-none"
              rows={1}
              style={{
                minHeight: '44px',
                maxHeight: '200px',
              }}
            />
          </div>

          {/* Bottom actions */}
          <div className="flex items-center justify-between px-2 py-1.5 border-t border-gray-200 dark:border-gray-800">
            <button className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 rounded text-gray-600 dark:text-gray-400 transition-colors text-xs font-medium" title="Mention someone">
              <AtSign size={14} className="inline mr-1" />
            </button>

            <button
              onClick={handleSendMessage}
              disabled={!messageInput.trim()}
              className="p-1.5 bg-green-600 hover:bg-green-700 disabled:bg-gray-300 dark:disabled:bg-gray-800 disabled:cursor-not-allowed rounded text-white transition-colors"
              title="Send message"
            >
              <Send size={16} />
            </button>
          </div>
        </div>

        <p className="mt-2 text-xs text-gray-500 dark:text-gray-400 px-1">
          <span className="font-semibold">Enter</span> to send, <span className="font-semibold">Shift + Enter</span> to add a new line
        </p>
      </div>
    </div>
  )
}
