import { useState, useRef, useEffect } from 'react'
import { MessageSquare, ChevronDown, Send, Share2, Zap, X } from 'lucide-react'
import { useSessionStore } from '@/stores/sessionStore'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

type AssistantMode = 'general' | 'data-analyst' | 'pair-programmer' | 'code-reviewer'

const ASSISTANT_MODES: Record<AssistantMode, { label: string; model: string; icon: string }> = {
  'general': { label: 'General Chat', model: 'qwen2.5-coder:7b-instruct', icon: '💬' },
  'data-analyst': { label: 'Data Analyst', model: 'qwen2.5-coder:7b-instruct', icon: '📊' },
  'pair-programmer': { label: 'Pair Programmer', model: 'qwen2.5-coder:14b-instruct', icon: '👨‍💻' },
  'code-reviewer': { label: 'Code Reviewer', model: 'deepseek-coder:6.7b', icon: '🔍' }
}

export function QuickChatDropdown() {
  const [isOpen, setIsOpen] = useState(false)
  const [mode, setMode] = useState<AssistantMode>('general')
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const dropdownRef = useRef<HTMLDivElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const isMountedRef = useRef(true)

  const { currentFile, currentQuery } = useSessionStore()

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
      abortControllerRef.current?.abort()
    }
  }, [])

  // Close dropdown with ESC key or X button only (not clicking outside)
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleEscape)
    }

    return () => {
      document.removeEventListener('keydown', handleEscape)
    }
  }, [isOpen])

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: Date.now()
    }

    setMessages(prev => [...prev, userMessage])
    const userContent = input.trim()
    setInput('')
    setIsLoading(true)

    // Create placeholder for assistant message
    const assistantId = (Date.now() + 1).toString()
    const assistantMessage: Message = {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: Date.now()
    }
    setMessages(prev => [...prev, assistantMessage])

    // Create abort controller for this request
    abortControllerRef.current = new AbortController()

    try {
      // Build context from current dataset and query results
      let contextPrompt = userContent
      if (mode === 'data-analyst') {
        const contextParts: string[] = []

        if (currentFile) {
          contextParts.push(`[Current dataset: ${currentFile.original_name || 'uploaded file'}]`)
        }

        if (currentQuery) {
          contextParts.push(`[Active query results: ${currentQuery.row_count || currentQuery.preview?.length || 0} rows, ${currentQuery.columns?.length || 0} columns]`)
          if (currentQuery.sql_query) {
            contextParts.push(`[Last SQL: ${currentQuery.sql_query}]`)
          }
        }

        if (contextParts.length > 0) {
          contextPrompt = `${contextParts.join('\n')}\n\n${userContent}`
        }
      }

      // Prepare messages for Ollama
      const chatHistory = messages.filter(msg => msg.content).map(msg => ({
        role: msg.role,
        content: msg.content
      }))
      chatHistory.push({
        role: 'user',
        content: contextPrompt
      })

      // Stream response from Ollama (direct call for performance - intentional)
      const response = await fetch('http://localhost:11434/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: ASSISTANT_MODES[mode].model,
          messages: chatHistory,
          stream: true
        }),
        signal: abortControllerRef.current.signal
      })

      if (!response.ok) {
        throw new Error(`Ollama API error: ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('No response stream available')
      }

      const decoder = new TextDecoder()
      let fullContent = ''

      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value, { stream: true })
          const lines = chunk.split('\n').filter(line => line.trim())

          for (const line of lines) {
            try {
              const json = JSON.parse(line)
              if (json.message?.content) {
                fullContent += json.message.content

                // Update message content in real-time
                setMessages(prev => prev.map(msg =>
                  msg.id === assistantId
                    ? { ...msg, content: fullContent }
                    : msg
                ))
              }

              // Check if stream is done
              if (json.done) {
                break
              }
            } catch (e) {
              console.warn('Failed to parse chunk:', line, e)
              // Skip invalid JSON lines
            }
          }
        }
      } catch (streamError) {
        console.error('Stream reading error:', streamError)
        throw streamError
      }

      if (!fullContent) {
        throw new Error('No response content received from model')
      }

    } catch (error) {
      console.error('Chat error:', error)

      // Only update state if still mounted
      if (isMountedRef.current) {
        // Update message with error
        setMessages(prev => prev.map(msg =>
          msg.id === assistantId
            ? { ...msg, content: `Error: ${error instanceof Error ? error.message : 'Failed to get response'}` }
            : msg
        ))
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false)
      }
      abortControllerRef.current = null
    }
  }

  const handleGenerateSQL = () => {
    if (currentFile) {
      const fileName = currentFile.filename || currentFile.original_name || 'uploaded file'
      setInput(`Generate SQL query for the loaded file: ${fileName}`)
    } else {
      setInput('Help me write a SQL query')
    }
  }

  const handlePortToMainChat = () => {
    // Port conversation to main chat tab (future enhancement: copy messages to main chat store)
    console.log('Porting conversation to main chat...')
  }

  const handleClear = () => {
    setMessages([])
    setInput('')
  }

  return (
    <>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-3 py-1.5 rounded-lg text-sm font-medium
          bg-white/50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700
          hover:bg-white dark:hover:bg-gray-800 transition-all"
      >
        <MessageSquare className="w-4 h-4" />
        <span className="hidden sm:inline">
          {ASSISTANT_MODES[mode].icon} {ASSISTANT_MODES[mode].label}
        </span>
      </button>

      {/* Full-Screen Overlay Modal */}
      {isOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={() => setIsOpen(false)}
        >
          <div className="w-full max-w-4xl h-[80vh] bg-white/95 dark:bg-gray-900/95 backdrop-blur-xl
            border border-gray-300 dark:border-gray-600 rounded-2xl shadow-2xl flex flex-col"
            onClick={(e) => e.stopPropagation()}
            ref={dropdownRef}
          >

          {/* Mode Selector */}
          <div className="p-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
            <div className="flex-1 px-3 py-1.5 text-sm font-medium text-gray-900 dark:text-gray-100">
              {ASSISTANT_MODES[mode].icon} {ASSISTANT_MODES[mode].label}
            </div>

            <div className="flex items-center gap-1">
              {messages.length > 0 && (
                <button
                  onClick={handleClear}
                  className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
                  title="Clear chat"
                >
                  <X className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                </button>
              )}
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
                title="Close (ESC)"
              >
                <X className="w-4 h-4 text-gray-600 dark:text-gray-400" />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.length === 0 ? (
              <div className="text-center text-sm text-gray-500 dark:text-gray-400 py-8">
                <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>Start a conversation with {ASSISTANT_MODES[mode].label}</p>
                {currentFile && (
                  <p className="mt-2 text-xs">
                    Current file: <span className="font-medium">{currentFile.filename || currentFile.original_name || 'Uploaded file'}</span>
                  </p>
                )}
              </div>
            ) : (
              messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] px-3 py-2 rounded-lg text-sm ${
                      msg.role === 'user'
                        ? 'bg-primary-500 text-white'
                        : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100'
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
              ))
            )}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 dark:bg-gray-800 px-3 py-2 rounded-lg text-sm">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-3 border-t border-gray-200 dark:border-gray-800">
            <div className="flex space-x-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSubmit()
                  }
                }}
                placeholder={`Ask ${ASSISTANT_MODES[mode].label}...`}
                className="flex-1 px-3 py-2 rounded border border-gray-200 dark:border-gray-700
                  bg-white dark:bg-gray-800 text-sm
                  focus:outline-none focus:ring-2 focus:ring-primary-500"
                disabled={isLoading}
              />
              <button
                onClick={handleSubmit}
                disabled={!input.trim() || isLoading}
                className="px-3 py-2 bg-primary-500 text-white rounded
                  hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed
                  transition-colors"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center justify-between mt-2 text-xs">
              <button
                onClick={handlePortToMainChat}
                disabled={messages.length === 0}
                className="flex items-center space-x-1 px-2 py-1 rounded
                  hover:bg-gray-100 dark:hover:bg-gray-800
                  disabled:opacity-50 disabled:cursor-not-allowed
                  text-gray-600 dark:text-gray-400"
              >
                <Share2 className="w-3 h-3" />
                <span>Port to Main Chat</span>
              </button>

              {mode === 'data-analyst' && currentFile && (
                <button
                  onClick={handleGenerateSQL}
                  className="flex items-center space-x-1 px-2 py-1 rounded
                    hover:bg-gray-100 dark:hover:bg-gray-800
                    text-gray-600 dark:text-gray-400"
                >
                  <Zap className="w-3 h-3" />
                  <span>Generate SQL</span>
                </button>
              )}
            </div>
          </div>
          </div>
        </div>
      )}
    </>
  )
}
