import { User, Bot, Copy, Check, FileText, Image as ImageIcon, File as FileIcon, Code, AlertTriangle } from 'lucide-react'
import { useState } from 'react'
import { ChatMessage as ChatMessageType } from '../stores/chatStore'

interface ChatMessageProps {
  message: ChatMessageType
  isStreaming?: boolean
}

export function ChatMessage({ message, isStreaming = false }: ChatMessageProps) {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    })
  }

  const formatFileSize = (bytes: number) => {
    if (!bytes) return ''
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase()

    if (['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp'].includes(ext || '')) {
      return <ImageIcon size={14} />
    }
    if (['pdf', 'doc', 'docx', 'txt', 'md'].includes(ext || '')) {
      return <FileText size={14} />
    }
    if (['js', 'ts', 'tsx', 'jsx', 'py', 'java', 'cpp', 'c', 'go', 'rs'].includes(ext || '')) {
      return <Code size={14} />
    }
    return <FileIcon size={14} />
  }

  // Extract code blocks for syntax highlighting
  const renderContent = (content: string) => {
    const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g
    const parts: JSX.Element[] = []
    let lastIndex = 0
    let match

    while ((match = codeBlockRegex.exec(content)) !== null) {
      // Add text before code block
      if (match.index > lastIndex) {
        const textBefore = content.substring(lastIndex, match.index)
        parts.push(
          <p key={`text-${lastIndex}`} className="whitespace-pre-wrap break-words">
            {textBefore}
          </p>
        )
      }

      // Add code block
      const language = match[1] || 'text'
      const code = match[2]
      parts.push(
        <div key={`code-${match.index}`} className="my-3 rounded-lg overflow-hidden">
          <div className="flex items-center justify-between bg-gray-800 px-4 py-2">
            <span className="text-xs text-gray-400 font-mono">{language}</span>
            <button
              onClick={() => copyToClipboard(code)}
              className="text-xs text-gray-400 hover:text-white flex items-center gap-1 transition-colors"
            >
              {copied ? (
                <>
                  <Check size={12} />
                  Copied
                </>
              ) : (
                <>
                  <Copy size={12} />
                  Copy
                </>
              )}
            </button>
          </div>
          <pre className="bg-gray-900 p-4 overflow-x-auto">
            <code className="text-sm text-gray-100 font-mono">{code}</code>
          </pre>
        </div>
      )

      lastIndex = match.index + match[0].length
    }

    // Add remaining text
    if (lastIndex < content.length) {
      const remaining = content.substring(lastIndex)
      parts.push(
        <p key={`text-${lastIndex}`} className="whitespace-pre-wrap break-words">
          {remaining}
        </p>
      )
    }

    return parts.length > 0 ? parts : <p className="whitespace-pre-wrap break-words">{content}</p>
  }

  return (
    <div
      className={`flex gap-3 mb-4 animate-fade-in ${
        isUser ? 'flex-row-reverse' : 'flex-row'
      }`}
    >
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-9 h-9 rounded-2xl flex items-center justify-center shadow-sm ${
          isUser
            ? 'bg-primary-600 text-white'
            : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-100'
        }`}
      >
        {isUser ? <User size={18} /> : <Bot size={18} />}
      </div>

      {/* Message Content */}
      <div className={`flex-1 ${isUser ? 'flex justify-end' : ''}`}>
        <div
          className={`max-w-[80%] rounded-2xl px-4 py-3 shadow-md transition-all hover:shadow-lg ${
            isUser
              ? 'bg-gradient-to-br from-primary-500 to-primary-600 text-white rounded-tr-sm'
              : 'bg-white/80 dark:bg-gray-800/80 backdrop-blur-xl text-gray-900 dark:text-gray-100 rounded-tl-sm border border-gray-200/50 dark:border-gray-700/50'
          }`}
        >
          {/* Message text */}
          <div className="text-sm leading-relaxed">
            {renderContent(message.content)}
          </div>

          {/* Files attached */}
          {message.files && message.files.length > 0 && (
            <div className="mt-3 pt-3 border-t border-white/20 dark:border-gray-700/50 space-y-2">
              {message.files.map((file) => (
                <div
                  key={file.id}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs ${
                    isUser
                      ? 'bg-white/20'
                      : 'bg-gray-100 dark:bg-gray-700/50'
                  }`}
                >
                  <div className={isUser ? 'text-white/80' : 'text-gray-500 dark:text-gray-400'}>
                    {getFileIcon(file.original_name)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className={`font-medium truncate ${
                      isUser ? 'text-white' : 'text-gray-700 dark:text-gray-200'
                    }`}>
                      {file.original_name}
                    </div>
                    {file.size && (
                      <div className={`text-xs ${
                        isUser ? 'text-white/70' : 'text-gray-500 dark:text-gray-400'
                      }`}>
                        {formatFileSize(file.size)}
                        {file.text_preview && ' • Text extracted'}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Unverified message badge (E2E encryption) */}
          {(message as any).verified === false && !isUser && (
            <div className="mt-3 pt-3 border-t border-white/20 dark:border-gray-700/50">
              <div className="flex items-center gap-2 px-2 py-1.5 bg-amber-100 dark:bg-amber-900/30 rounded text-amber-800 dark:text-amber-300">
                <AlertTriangle className="w-3 h-3 flex-shrink-0" />
                <span className="text-xs font-medium">Unverified</span>
              </div>
            </div>
          )}

          {/* Metadata */}
          <div
            className={`mt-2 text-xs flex items-center gap-2 ${
              isUser ? 'text-white/70' : 'text-gray-500 dark:text-gray-400'
            }`}
          >
            <span>{formatTime(message.timestamp)}</span>
            {message.model && (
              <>
                <span>•</span>
                <span className="font-mono">{message.model}</span>
              </>
            )}
            {message.tokens && (
              <>
                <span>•</span>
                <span>{message.tokens} tokens</span>
              </>
            )}
            {isStreaming && (
              <>
                <span>•</span>
                <span className="animate-pulse">●</span>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
