import { useEffect, useState, useRef } from 'react'
import DOMPurify from 'dompurify'
import { Hash } from 'lucide-react'
import { useTeamChatStore } from '../../stores/teamChatStore'
import { showToast, showUndoToast } from '@/lib/toast'
import { MessageList } from './MessageList'
import { MessageInput } from './MessageInput'
import { LocalMessage } from './types'
import { EMOJIS } from './EmojiPicker'

interface TeamChatWindowProps {
  mode: 'solo' | 'p2p'
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
        if (e.key === 'ArrowRight') {
          e.preventDefault()
          setSelectedEmojiIndex((prev) => (prev + 1) % EMOJIS.length)
        } else if (e.key === 'ArrowLeft') {
          e.preventDefault()
          setSelectedEmojiIndex((prev) => (prev - 1 + EMOJIS.length) % EMOJIS.length)
        } else if (e.key === 'ArrowDown') {
          e.preventDefault()
          setSelectedEmojiIndex((prev) => (prev + 8) % EMOJIS.length)
        } else if (e.key === 'ArrowUp') {
          e.preventDefault()
          setSelectedEmojiIndex((prev) => (prev - 8 + EMOJIS.length) % EMOJIS.length)
        } else if (e.key === 'Enter') {
          e.preventDefault()
          insertEmoji(EMOJIS[selectedEmojiIndex])
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [showEmojiPicker, selectedEmojiIndex])

  const handleSendMessage = () => {
    if ((!messageInput.trim() && !uploadedFile) || !activeChannelId) return

    const messageContent = messageInput.trim()
    const messageId = `msg_${Date.now()}`

    const newMessage: LocalMessage = {
      id: messageId,
      channel_id: activeChannelId,
      sender_name: mode === 'solo' ? 'You' : 'Me',
      content: messageContent,
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

    // Show toast with undo option
    showUndoToast(
      uploadedFile ? 'File sent' : 'Message sent',
      () => {
        // Undo: remove the message
        setMessages(prev => prev.filter(m => m.id !== messageId))
        if (mode === 'solo' && activeChannelId) {
          const updatedMessages = messages.filter(m => m.id !== messageId)
          localStorage.setItem(`solo_messages_${activeChannelId}`, JSON.stringify(updatedMessages))
        }
      }
    )
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
    // Store the deleted message for undo
    const deletedMessage = messages.find(m => m.id === messageId)
    const updatedMessages = messages.filter(m => m.id !== messageId)
    setMessages(updatedMessages)

    // Update localStorage immediately
    if (mode === 'solo' && activeChannelId) {
      localStorage.setItem(`solo_messages_${activeChannelId}`, JSON.stringify(updatedMessages))
    }

    // Show undo toast
    if (deletedMessage) {
      showUndoToast(
        'Message deleted',
        () => {
          // Undo: restore the deleted message
          setMessages(prev => [...prev, deletedMessage].sort((a, b) =>
            new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
          ))
          if (mode === 'solo' && activeChannelId) {
            const restored = [...updatedMessages, deletedMessage].sort((a, b) =>
              new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
            )
            localStorage.setItem(`solo_messages_${activeChannelId}`, JSON.stringify(restored))
          }
        }
      )
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

    // Sanitize output to prevent XSS when injecting HTML
    return DOMPurify.sanitize(rendered, {
      ALLOWED_TAGS: ['strong', 'em', 'code', 'a', 'p', 'br'],
      ALLOWED_ATTR: ['href', 'target', 'rel']
    })
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
      <MessageList
        messages={messages}
        activeChannelName={activeChannel?.name || ''}
        mode={mode}
        editingMessageId={editingMessageId}
        editingContent={editingContent}
        onChangeEditingContent={setEditingContent}
        onSaveEdit={handleSaveEdit}
        onCancelEdit={handleCancelEdit}
        onDeleteMessage={handleDeleteMessage}
        formatTimestamp={formatTimestamp}
        renderMarkdown={renderMarkdown}
        onEditMessage={handleEditMessage}
        messagesEndRef={messagesEndRef}
      />

      {/* Message Input */}
      <MessageInput
        mode={mode}
        messageInput={messageInput}
        onChangeMessageInput={setMessageInput}
        onSendMessage={handleSendMessage}
        onKeyDown={handleKeyDown}
        uploadedFile={uploadedFile}
        onFileSelect={handleFileSelect}
        onFileUploadClick={handleFileUpload}
        onRemoveFile={removeFile}
        onToggleEmojiPicker={() => setShowEmojiPicker(!showEmojiPicker)}
        showEmojiPicker={showEmojiPicker}
        inputRef={inputRef}
        fileInputRef={fileInputRef}
        onInsertMention={insertMention}
        onBold={handleBold}
        onItalic={handleItalic}
        onCode={handleCode}
        onLink={handleLink}
        activeChannelName={activeChannel?.name || ''}
        selectedEmojiIndex={selectedEmojiIndex}
        onSelectEmoji={insertEmoji}
        onChangeEmojiIndex={setSelectedEmojiIndex}
        emojiPickerRef={emojiPickerRef}
      />
    </div>
  )
}
