/**
 * CodeChat - Chat interface for Code Tab
 * Integrates with file context for code-aware conversations
 * Phase 4: Chat Integration
 */

import { useState, useRef, useEffect } from 'react'
import { Send, Code, FileCode, X, Loader2 } from 'lucide-react'
import { ChatMessage } from './ChatMessage'
import toast from 'react-hot-toast'

interface CodeChatProps {
  currentFile?: string
  fileContent?: string
  onClose?: () => void
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  fileContext?: {
    path: string
    snippet?: string
  }
}

export function CodeChat({ currentFile, fileContent, onClose }: CodeChatProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [includeFileContext, setIncludeFileContext] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: Date.now(),
      fileContext: includeFileContext && currentFile ? {
        path: currentFile,
        snippet: fileContent?.split('\n').slice(0, 50).join('\n') // First 50 lines
      } : undefined
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsStreaming(true)
    setStreamingContent('')

    try {
      // Build context-aware prompt
      let prompt = input
      if (userMessage.fileContext) {
        prompt = `File: ${userMessage.fileContext.path}\n\n\`\`\`\n${userMessage.fileContext.snippet}\n\`\`\`\n\nQuestion: ${input}`
      }

      // Use Ollama streaming endpoint
      const eventSource = new EventSource(
        `/api/v1/chat/stream?` +
        new URLSearchParams({
          prompt: prompt,
          model: 'qwen2.5-coder:7b', // Code-focused model
          session_id: 'code_chat_' + Date.now()
        })
      )

      eventSourceRef.current = eventSource

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          if (data.done) {
            // Finalize assistant message
            const assistantMessage: Message = {
              id: Date.now().toString(),
              role: 'assistant',
              content: streamingContent,
              timestamp: Date.now()
            }
            setMessages(prev => [...prev, assistantMessage])
            setStreamingContent('')
            setIsStreaming(false)
            eventSource.close()
          } else if (data.response) {
            // Append chunk
            setStreamingContent(prev => prev + data.response)
          }
        } catch (err) {
          console.error('Error parsing SSE:', err)
        }
      }

      eventSource.onerror = (error) => {
        console.error('SSE error:', error)
        toast.error('Connection error')
        setIsStreaming(false)
        eventSource.close()
      }

    } catch (err) {
      console.error('Error sending message:', err)
      toast.error('Failed to send message')
      setIsStreaming(false)
    }
  }

  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-800">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <Code className="w-5 h-5 text-primary-600" />
          <h3 className="font-semibold text-gray-900 dark:text-gray-100">
            Code Assistant
          </h3>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
          >
            <X className="w-4 h-4 text-gray-500" />
          </button>
        )}
      </div>

      {/* File Context Badge */}
      {currentFile && (
        <div className="px-4 py-2 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={includeFileContext}
              onChange={(e) => setIncludeFileContext(e.target.checked)}
              className="rounded"
            />
            <FileCode className="w-4 h-4 text-gray-500" />
            <span className="text-gray-700 dark:text-gray-300">
              Include context from: <span className="font-mono text-xs">{currentFile}</span>
            </span>
          </label>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center mt-20 space-y-3">
            <Code className="w-16 h-16 mx-auto text-gray-300 dark:text-gray-600" />
            <div>
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Ask about your code
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {currentFile
                  ? 'Context from current file will be included'
                  : 'Open a file to include context'}
              </p>
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <div key={msg.id} className="space-y-1">
                {msg.fileContext && (
                  <div className="text-xs text-gray-500 dark:text-gray-400 font-mono mb-1">
                    📄 {msg.fileContext.path}
                  </div>
                )}
                <ChatMessage
                  role={msg.role}
                  content={msg.content}
                  timestamp={new Date(msg.timestamp)}
                />
              </div>
            ))}

            {/* Streaming message */}
            {isStreaming && streamingContent && (
              <ChatMessage
                role="assistant"
                content={streamingContent}
                timestamp={new Date()}
              />
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSend()
              }
            }}
            placeholder={currentFile ? 'Ask about this code...' : 'Ask a question...'}
            disabled={isStreaming}
            className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            className="p-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isStreaming ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}
