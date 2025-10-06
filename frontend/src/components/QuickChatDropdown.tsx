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

  const { currentFile } = useSessionStore()

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
      abortControllerRef.current?.abort()
    }
  }, [])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
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
      // Build context from current dataset
      let contextPrompt = userContent
      if (currentFile && mode === 'data-analyst') {
        contextPrompt = `[Current dataset: ${currentFile}]\n\n${userContent}`
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

      // Stream response from Ollama
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
    // TODO: Implement SQL generation from current context
    if (currentFile) {
      setInput(`Generate SQL query for the loaded file: ${currentFile}`)
    } else {
      setInput('Help me write a SQL query')
    }
  }

  const handlePortToMainChat = () => {
    // TODO: Implement port to main chat tab
    console.log('Porting conversation to main chat...')
  }

  const handleClear = () => {
    setMessages([])
    setInput('')
  }

  return (
    <div className="relative" ref={dropdownRef}>
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
        <ChevronDown className={`w-3 h-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-96 max-w-[calc(100vw-2rem)]
          bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700
          rounded-lg shadow-xl z-50 flex flex-col max-h-[600px]">

          {/* Mode Selector */}
          <div className="p-3 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as AssistantMode)}
              className="flex-1 px-3 py-1.5 rounded border border-gray-200 dark:border-gray-700
                bg-white dark:bg-gray-800 text-sm"
            >
              {Object.entries(ASSISTANT_MODES).map(([key, config]) => (
                <option key={key} value={key}>
                  {config.icon} {config.label}
                </option>
              ))}
            </select>

            {messages.length > 0 && (
              <button
                onClick={handleClear}
                className="ml-2 p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
                title="Clear chat"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-[300px] max-h-[400px]">
            {messages.length === 0 ? (
              <div className="text-center text-sm text-gray-500 dark:text-gray-400 py-8">
                <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>Start a conversation with {ASSISTANT_MODES[mode].label}</p>
                {currentFile && (
                  <p className="mt-2 text-xs">
                    Current file: <span className="font-medium">{currentFile}</span>
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
      )}
    </div>
  )
}
