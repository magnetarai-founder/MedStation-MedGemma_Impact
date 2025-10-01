import { User, Bot, Copy, Check } from 'lucide-react'
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
      className={`flex gap-3 mb-6 ${
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
          className={`max-w-[80%] rounded-3xl px-5 py-3 shadow-sm ${
            isUser
              ? 'bg-primary-600 text-white rounded-tr-md'
              : 'bg-white/60 dark:bg-gray-800/60 backdrop-blur-xl text-gray-900 dark:text-gray-100 rounded-tl-md border border-white/20 dark:border-gray-700/30'
          }`}
        >
          {/* Message text */}
          <div className="text-sm leading-relaxed">
            {renderContent(message.content)}
          </div>

          {/* Files attached */}
          {message.files && message.files.length > 0 && (
            <div className="mt-2 pt-2 border-t border-white/20 dark:border-gray-700">
              {message.files.map((file) => (
                <div
                  key={file.id}
                  className="text-xs opacity-75 flex items-center gap-1"
                >
                  📎 {file.original_name}
                </div>
              ))}
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
