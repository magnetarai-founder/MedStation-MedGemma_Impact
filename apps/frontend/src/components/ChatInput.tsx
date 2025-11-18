import { useState, useRef, KeyboardEvent, useEffect } from 'react'
import { Send, Paperclip, X } from 'lucide-react'
import { useChatStore } from '../stores/chatStore'
import { api } from '../lib/api'

interface ChatInputProps {
  onSend: (content: string, files?: File[]) => void
  disabled?: boolean
  placeholder?: string
}

export function ChatInput({ onSend, disabled = false, placeholder = 'Type a message...' }: ChatInputProps) {
  const [input, setInput] = useState('')
  const [attachedFiles, setAttachedFiles] = useState<File[]>([])
  const [tokenCount, setTokenCount] = useState({ total: 0, max: 200000, percentage: 0 })
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { activeChatId, messages } = useChatStore()

  const handleSend = () => {
    if (!input.trim() && attachedFiles.length === 0) return
    if (disabled) return

    onSend(input.trim(), attachedFiles)
    setInput('')
    setAttachedFiles([])

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)

    // Auto-resize textarea
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px'
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    setAttachedFiles(prev => [...prev, ...files])
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const removeFile = (index: number) => {
    setAttachedFiles(prev => prev.filter((_, i) => i !== index))
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  // Fetch token count when chat changes or messages update
  useEffect(() => {
    if (!activeChatId) return

    const fetchTokenCount = async () => {
      try {
        const response = await fetch(`/api/v1/chat/sessions/${activeChatId}/token-count`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        })

        if (!response.ok) {
          throw new Error(`Token count fetch failed: ${response.status}`)
        }

        const data = await response.json()
        setTokenCount({
          total: data.total_tokens,
          max: data.max_tokens,
          percentage: data.percentage
        })
      } catch (error) {
        console.error('Failed to fetch token count:', error)
      }
    }

    fetchTokenCount()
  }, [activeChatId, messages.length])

  return (
    <div className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
      {/* Attached Files */}
      {attachedFiles.length > 0 && (
        <div className="px-4 pt-3 flex flex-wrap gap-2">
          {attachedFiles.map((file, index) => (
            <div
              key={index}
              className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm"
            >
              <Paperclip size={14} className="text-gray-500" />
              <span className="text-gray-700 dark:text-gray-300">
                {file.name}
              </span>
              <span className="text-gray-500 text-xs">
                ({formatFileSize(file.size)})
              </span>
              <button
                onClick={() => removeFile(index)}
                className="ml-1 text-gray-500 hover:text-red-600 transition-colors"
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Input Area */}
      <div className="p-4 flex items-end gap-2">
        {/* File Attach Button */}
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
          className="flex-shrink-0 p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          title="Attach file"
        >
          <Paperclip size={20} />
        </button>

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={handleFileSelect}
        />

        {/* Text Input */}
        <textarea
          id="chat-message-input"
          name="message"
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          aria-label="Chat message"
          autoComplete="off"
          className="flex-1 resize-none bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
          style={{ maxHeight: '200px' }}
        />

        {/* Send Button */}
        <button
          onClick={handleSend}
          disabled={disabled || (!input.trim() && attachedFiles.length === 0)}
          className="flex-shrink-0 p-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          title="Send message"
        >
          <Send size={18} />
        </button>
      </div>

      {/* Helper Text with Token Counter */}
      <div className="px-4 pb-3 flex justify-between items-center text-xs text-gray-500 dark:text-gray-400">
        <span>Press Enter to send, Shift+Enter for new line</span>
        {activeChatId && (
          <span
            className={`font-mono ${
              tokenCount.percentage > 95 ? 'text-red-600 dark:text-red-400' :
              tokenCount.percentage > 90 ? 'text-orange-600 dark:text-orange-400' :
              ''
            }`}
          >
            {tokenCount.total.toLocaleString()} / {tokenCount.max.toLocaleString()} tokens
          </span>
        )}
      </div>
    </div>
  )
}
