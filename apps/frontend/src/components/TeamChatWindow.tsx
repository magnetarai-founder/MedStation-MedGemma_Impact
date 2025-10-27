import { useEffect, useState, useRef } from 'react'
import { Send, Smile, Paperclip, Hash, Bold, Italic, Code, Link as LinkIcon, AtSign, X, Pencil, Trash2, Check } from 'lucide-react'
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
  file?: {
    name: string
    size: number
    type: string
    url: string
  }
}

export function TeamChatWindow({ mode }: TeamChatWindowProps) {
  const {
    channels,
    activeChannelId,
  } = useTeamChatStore()

  const [messageInput, setMessageInput] = useState('')
  const [messages, setMessages] = useState<LocalMessage[]>([])
  const [showEmojiPicker, setShowEmojiPicker] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null)
  const [editingContent, setEditingContent] = useState('')
  const [selectedEmojiIndex, setSelectedEmojiIndex] = useState(0)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const emojiPickerRef = useRef<HTMLDivElement>(null)

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

  // Close emoji picker when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (emojiPickerRef.current && !emojiPickerRef.current.contains(event.target as Node)) {
        setShowEmojiPicker(false)
      }
    }

    if (showEmojiPicker) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showEmojiPicker])

  // Keyboard shortcuts for emoji picker
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd+Control+Space to open emoji picker (macOS shortcut)
      if (e.metaKey && e.ctrlKey && e.code === 'Space') {
        e.preventDefault()
        setShowEmojiPicker(!showEmojiPicker)
        return
      }

      // ESC to close emoji picker
      if (e.key === 'Escape' && showEmojiPicker) {
        e.preventDefault()
        setShowEmojiPicker(false)
        inputRef.current?.focus()
        return
      }

      // Arrow key navigation in emoji picker
      if (showEmojiPicker) {
        const emojis = ['😀', '😃', '😄', '😁', '😆', '😅', '🤣', '😂',
          '🙂', '🙃', '😉', '😊', '😇', '🥰', '😍', '🤩',
          '😘', '😗', '😚', '😙', '😋', '😛', '😜', '🤪',
          '😎', '🤓', '🧐', '🤨', '🤔', '🤗', '🤭', '🤫',
          '🤥', '😶', '😐', '😑', '😬', '🙄', '😏', '😌',
          '😔', '😪', '🤤', '😴', '😷', '🤒', '🤕', '🤢',
          '👍', '👎', '👌', '✌️', '🤞', '🤝', '👏', '🙌',
          '❤️', '💙', '💚', '💛', '🧡', '💜', '🖤', '🤍',
          '✅', '❌', '⭐', '🔥', '💯', '🎉', '🎊', '🚀']

        if (e.key === 'ArrowRight') {
          e.preventDefault()
          setSelectedEmojiIndex((prev) => (prev + 1) % emojis.length)
        } else if (e.key === 'ArrowLeft') {
          e.preventDefault()
          setSelectedEmojiIndex((prev) => (prev - 1 + emojis.length) % emojis.length)
        } else if (e.key === 'ArrowDown') {
          e.preventDefault()
          setSelectedEmojiIndex((prev) => (prev + 8) % emojis.length)
        } else if (e.key === 'ArrowUp') {
          e.preventDefault()
          setSelectedEmojiIndex((prev) => (prev - 8 + emojis.length) % emojis.length)
        } else if (e.key === 'Enter') {
          e.preventDefault()
          insertEmoji(emojis[selectedEmojiIndex])
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [showEmojiPicker, selectedEmojiIndex])

  const handleSendMessage = () => {
    if ((!messageInput.trim() && !uploadedFile) || !activeChannelId) return

    const newMessage: LocalMessage = {
      id: `msg_${Date.now()}`,
      channel_id: activeChannelId,
      sender_name: mode === 'solo' ? 'You' : 'Me',
      content: messageInput.trim(),
      timestamp: new Date().toISOString(),
      type: uploadedFile ? 'file' : 'text',
      ...(uploadedFile && {
        file: {
          name: uploadedFile.name,
          size: uploadedFile.size,
          type: uploadedFile.type,
          url: URL.createObjectURL(uploadedFile)
        }
      })
    }

    setMessages([...messages, newMessage])
    setMessageInput('')
    setUploadedFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
    inputRef.current?.focus()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Cmd+B for bold
    if (e.metaKey && e.key === 'b') {
      e.preventDefault()
      handleBold()
      return
    }

    // Cmd+I for italic
    if (e.metaKey && e.key === 'i') {
      e.preventDefault()
      handleItalic()
      return
    }

    // Cmd+Shift+C for code
    if (e.metaKey && e.shiftKey && e.key === 'c') {
      e.preventDefault()
      handleCode()
      return
    }

    // Cmd+K for link
    if (e.metaKey && e.key === 'k') {
      e.preventDefault()
      handleLink()
      return
    }

    // Enter to send
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleDeleteMessage = (messageId: string) => {
    const updatedMessages = messages.filter(m => m.id !== messageId)
    setMessages(updatedMessages)

    // Update localStorage immediately
    if (mode === 'solo' && activeChannelId) {
      localStorage.setItem(`solo_messages_${activeChannelId}`, JSON.stringify(updatedMessages))
    }
  }

  const handleEditMessage = (messageId: string) => {
    const message = messages.find(m => m.id === messageId)
    if (message && message.type === 'text') {
      setEditingMessageId(messageId)
      setEditingContent(message.content)
    }
  }

  const handleSaveEdit = (messageId: string) => {
    if (!editingContent.trim()) return

    const updatedMessages = messages.map(m =>
      m.id === messageId
        ? { ...m, content: editingContent.trim() }
        : m
    )
    setMessages(updatedMessages)

    // Update localStorage immediately
    if (mode === 'solo' && activeChannelId) {
      localStorage.setItem(`solo_messages_${activeChannelId}`, JSON.stringify(updatedMessages))
    }

    setEditingMessageId(null)
    setEditingContent('')
  }

  const handleCancelEdit = () => {
    setEditingMessageId(null)
    setEditingContent('')
  }

  // Text formatting functions
  const insertFormatting = (prefix: string, suffix: string = prefix) => {
    const textarea = inputRef.current
    if (!textarea) return

    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const selectedText = messageInput.substring(start, end)
    const before = messageInput.substring(0, start)
    const after = messageInput.substring(end)

    const newText = `${before}${prefix}${selectedText || 'text'}${suffix}${after}`
    setMessageInput(newText)

    // Set cursor position after formatting
    setTimeout(() => {
      const newPos = selectedText ? end + prefix.length + suffix.length : start + prefix.length
      textarea.setSelectionRange(newPos, newPos)
      textarea.focus()
    }, 0)
  }

  const handleBold = () => insertFormatting('**')
  const handleItalic = () => insertFormatting('*')
  const handleCode = () => insertFormatting('`')
  const handleLink = () => insertFormatting('[', '](url)')

  // Emoji handling
  const insertEmoji = (emoji: string) => {
    const textarea = inputRef.current
    if (!textarea) return

    const start = textarea.selectionStart
    const before = messageInput.substring(0, start)
    const after = messageInput.substring(start)

    setMessageInput(`${before}${emoji}${after}`)
    setShowEmojiPicker(false)

    setTimeout(() => {
      textarea.setSelectionRange(start + emoji.length, start + emoji.length)
      textarea.focus()
    }, 0)
  }

  // File handling
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setUploadedFile(file)
    }
  }

  const handleFileUpload = () => {
    fileInputRef.current?.click()
  }

  const removeFile = () => {
    setUploadedFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  // Mention handling
  const insertMention = () => {
    const textarea = inputRef.current
    if (!textarea) return

    const start = textarea.selectionStart
    const before = messageInput.substring(0, start)
    const after = messageInput.substring(start)

    setMessageInput(`${before}@${after}`)

    setTimeout(() => {
      textarea.setSelectionRange(start + 1, start + 1)
      textarea.focus()
    }, 0)
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

  const renderMarkdown = (text: string) => {
    // Simple markdown rendering
    let rendered = text

    // Bold: **text**
    rendered = rendered.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')

    // Italic: *text*
    rendered = rendered.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>')

    // Code: `text`
    rendered = rendered.replace(/`(.+?)`/g, '<code class="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-sm font-mono text-pink-600 dark:text-pink-400">$1</code>')

    // Links: [text](url)
    rendered = rendered.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-blue-600 dark:text-blue-400 hover:underline">$1</a>')

    return rendered
  }

  if (!activeChannelId) {
    return (
      <div className="h-full flex items-center justify-center">
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
    <div className="h-full flex flex-col">
      {/* Channel Header (Slack-style) */}
      <div className="flex-shrink-0 px-4 py-3 border-b border-gray-200 dark:border-gray-700">
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
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {messages.length === 0 ? (
          <div className="mt-8">
            <div className="w-12 h-12 bg-gray-100 dark:bg-gray-900 rounded-lg flex items-center justify-center mb-2">
              <Hash size={24} className="text-gray-400 dark:text-gray-600" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-1">
              This is the very beginning of the <span className="text-gray-700 dark:text-gray-300">#{activeChannel?.name}</span> channel
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {mode === 'solo'
                ? 'This channel is for you to organize your thoughts and files.'
                : 'This channel is for team-wide communication and collaboration.'}
            </p>
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
                      {editingMessageId === message.id ? (
                        <div className="space-y-2">
                          <textarea
                            value={editingContent}
                            onChange={(e) => setEditingContent(e.target.value)}
                            className="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded text-sm focus:outline-none focus:border-primary-500 resize-none"
                            rows={3}
                            autoFocus
                          />
                          <div className="flex gap-2">
                            <button
                              onClick={() => handleSaveEdit(message.id)}
                              className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white rounded text-sm flex items-center gap-1"
                            >
                              <Check size={14} />
                              Save
                            </button>
                            <button
                              onClick={handleCancelEdit}
                              className="px-3 py-1 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded text-sm"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : message.type === 'file' && message.file ? (
                        <div className="space-y-2">
                          {message.content && (
                            <div dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }} />
                          )}
                          <a
                            href={message.file.url}
                            download={message.file.name}
                            className="flex items-center gap-2 p-3 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors max-w-sm"
                          >
                            <Paperclip size={16} className="text-gray-500 dark:text-gray-400 flex-shrink-0" />
                            <div className="flex-1 min-w-0">
                              <div className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                                {message.file.name}
                              </div>
                              <div className="text-xs text-gray-500 dark:text-gray-400">
                                {(message.file.size / 1024).toFixed(1)} KB
                              </div>
                            </div>
                          </a>
                        </div>
                      ) : (
                        <div dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }} />
                      )}
                    </div>
                  </div>

                  {/* Message hover actions (Slack-style) */}
                  {editingMessageId !== message.id && (
                    <div className="opacity-0 group-hover:opacity-100 flex items-start gap-0.5 transition-opacity">
                      <button
                        onClick={() => handleEditMessage(message.id)}
                        className="p-1 hover:bg-gray-200 dark:hover:bg-gray-800 rounded text-gray-600 dark:text-gray-400"
                        title="Edit message"
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        onClick={() => handleDeleteMessage(message.id)}
                        className="p-1 hover:bg-gray-200 dark:hover:bg-gray-800 rounded text-gray-600 dark:text-gray-400"
                        title="Delete message"
                      >
                        <Trash2 size={14} />
                      </button>
                      <button
                        className="p-1 hover:bg-gray-200 dark:hover:bg-gray-800 rounded text-gray-600 dark:text-gray-400"
                        title="Add reaction"
                      >
                        <Smile size={16} />
                      </button>
                    </div>
                  )}
                </div>
              )
            })}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Message Input (Slack-style) */}
      <div className="flex-shrink-0 px-4 pb-6 relative">
        <div className="border-2 border-gray-300 dark:border-gray-700 rounded-lg focus-within:border-gray-400 dark:focus-within:border-gray-600 transition-colors">
          {/* Formatting toolbar */}
          <div className="flex items-center gap-1 px-2 py-1.5 border-b border-gray-200 dark:border-gray-700">
            <button onClick={handleBold} className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 rounded text-gray-600 dark:text-gray-400 transition-colors" title="Bold">
              <Bold size={16} />
            </button>
            <button onClick={handleItalic} className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 rounded text-gray-600 dark:text-gray-400 transition-colors" title="Italic">
              <Italic size={16} />
            </button>
            <button onClick={handleCode} className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 rounded text-gray-600 dark:text-gray-400 transition-colors" title="Code">
              <Code size={16} />
            </button>
            <button onClick={handleLink} className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 rounded text-gray-600 dark:text-gray-400 transition-colors" title="Link">
              <LinkIcon size={16} />
            </button>
            <div className="flex-1"></div>
            <button onClick={() => setShowEmojiPicker(!showEmojiPicker)} className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 rounded text-gray-600 dark:text-gray-400 transition-colors" title="Emoji">
              <Smile size={16} />
            </button>
            <button onClick={handleFileUpload} className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 rounded text-gray-600 dark:text-gray-400 transition-colors" title="Attach file">
              <Paperclip size={16} />
            </button>
          </div>

          {/* Emoji Picker */}
          {showEmojiPicker && (
            <div ref={emojiPickerRef} className="absolute bottom-full mb-2 right-20 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl p-3 z-50">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Emoji</span>
                <button
                  onClick={() => setShowEmojiPicker(false)}
                  className="p-1 hover:bg-gray-100 dark:hover:bg-gray-900 rounded"
                >
                  <X size={14} className="text-gray-500 dark:text-gray-400" />
                </button>
              </div>
              <div className="grid grid-cols-8 gap-1 max-w-xs">
                {['😀', '😃', '😄', '😁', '😆', '😅', '🤣', '😂',
                  '🙂', '🙃', '😉', '😊', '😇', '🥰', '😍', '🤩',
                  '😘', '😗', '😚', '😙', '😋', '😛', '😜', '🤪',
                  '😎', '🤓', '🧐', '🤨', '🤔', '🤗', '🤭', '🤫',
                  '🤥', '😶', '😐', '😑', '😬', '🙄', '😏', '😌',
                  '😔', '😪', '🤤', '😴', '😷', '🤒', '🤕', '🤢',
                  '👍', '👎', '👌', '✌️', '🤞', '🤝', '👏', '🙌',
                  '❤️', '💙', '💚', '💛', '🧡', '💜', '🖤', '🤍',
                  '✅', '❌', '⭐', '🔥', '💯', '🎉', '🎊', '🚀'
                ].map((emoji, index) => (
                  <button
                    key={emoji}
                    onClick={() => insertEmoji(emoji)}
                    className={`text-xl p-1.5 rounded transition-colors ${
                      index === selectedEmojiIndex
                        ? 'bg-primary-500 text-white'
                        : 'hover:bg-gray-100 dark:hover:bg-gray-900'
                    }`}
                  >
                    {emoji}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileSelect}
            className="hidden"
          />

          {/* File preview */}
          {uploadedFile && (
            <div className="px-3 py-2 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2">
                <Paperclip size={16} className="text-gray-500 dark:text-gray-400" />
                <span className="text-sm text-gray-700 dark:text-gray-300 flex-1 truncate">
                  {uploadedFile.name}
                </span>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {(uploadedFile.size / 1024).toFixed(1)} KB
                </span>
                <button
                  onClick={removeFile}
                  className="p-1 hover:bg-gray-200 dark:hover:bg-gray-800 rounded"
                  title="Remove file"
                >
                  <X size={14} className="text-gray-500 dark:text-gray-400" />
                </button>
              </div>
            </div>
          )}

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
          <div className="flex items-center justify-between px-2 py-1.5 border-t border-gray-200 dark:border-gray-700">
            <button onClick={insertMention} className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 rounded text-gray-600 dark:text-gray-400 transition-colors text-xs font-medium" title="Mention someone">
              <AtSign size={14} className="inline mr-1" />
            </button>

            <button
              onClick={handleSendMessage}
              disabled={!messageInput.trim() && !uploadedFile}
              className="p-1.5 bg-green-600 hover:bg-green-700 disabled:bg-gray-300 dark:disabled:bg-gray-800 disabled:cursor-not-allowed rounded text-white transition-colors"
              title="Send message"
            >
              <Send size={16} />
            </button>
          </div>
        </div>

        <p className="mt-2 text-xs text-gray-500 dark:text-gray-400 px-1">
          <span className="font-semibold">⌘B</span> bold · <span className="font-semibold">⌘I</span> italic · <span className="font-semibold">⌘K</span> link · <span className="font-semibold">⌘⌃Space</span> emoji · <span className="font-semibold">Enter</span> send · <span className="font-semibold">⇧Enter</span> new line
        </p>
      </div>
    </div>
  )
}
