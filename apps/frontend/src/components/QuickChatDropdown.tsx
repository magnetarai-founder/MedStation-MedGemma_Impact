import { useState, useRef, useEffect } from 'react'
import { Cloud, Send, Share2, Zap, X, ChevronDown } from 'lucide-react'
import { useSessionStore } from '@/stores/sessionStore'
import { useOllamaStore } from '@/stores/ollamaStore'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

interface QuickChatDropdownProps {
  isOpen?: boolean
  onToggle?: () => void
}

const DEFAULT_MODEL = 'qwen2.5-coder:7b-instruct'

export function QuickChatDropdown({ isOpen: controlledIsOpen, onToggle }: QuickChatDropdownProps = {}) {
  const [internalIsOpen, setInternalIsOpen] = useState(false)
  const isOpen = controlledIsOpen !== undefined ? controlledIsOpen : internalIsOpen
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [selectedModel, setSelectedModel] = useState(DEFAULT_MODEL)
  const [showModelSelect, setShowModelSelect] = useState(false)

  const dropdownRef = useRef<HTMLDivElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const isMountedRef = useRef(true)

  const { currentFile, currentQuery } = useSessionStore()
  const { serverStatus } = useOllamaStore()

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
      abortControllerRef.current?.abort()
    }
  }, [])

  const handleToggle = () => {
    if (onToggle) {
      onToggle()
    } else {
      setInternalIsOpen(!internalIsOpen)
    }
  }

  const handleClose = () => {
    if (onToggle) {
      onToggle()
    } else {
      setInternalIsOpen(false)
    }
  }

  // Close dropdown with ESC key
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        handleClose()
      }
    }

    document.addEventListener('keydown', handleEscape)
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
      // Prepare messages for Ollama
      const chatHistory = messages.filter(msg => msg.content).map(msg => ({
        role: msg.role,
        content: msg.content
      }))
      chatHistory.push({
        role: 'user',
        content: userContent
      })

      // Stream response from Ollama (direct call for performance - intentional)
      const response = await fetch('http://localhost:11434/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: selectedModel,
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
    <div className="relative">
      {/* Trigger Button */}
      <button
        onClick={handleToggle}
        className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400"
        title="AI Chat"
      >
        <Cloud size={20} />
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div
          className="absolute top-full right-0 mt-2 w-96 h-[500px] bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg shadow-xl flex flex-col z-50"
          ref={dropdownRef}
        >

          {/* Header */}
          <div className="p-3 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                AI Chat
              </div>

              {/* Clear chat button (only show when there are messages) */}
              {messages.length > 0 && (
                <button
                  onClick={handleClear}
                  className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
                  title="Clear chat"
                >
                  <X className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                </button>
              )}
            </div>

            {/* Model Selector */}
            <div className="relative">
              <button
                onClick={() => setShowModelSelect(!showModelSelect)}
                className="w-full px-3 py-1.5 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 rounded text-left text-xs text-gray-700 dark:text-gray-300 flex items-center justify-between transition-colors"
              >
                <span className="truncate">{selectedModel}</span>
                <ChevronDown className="w-3 h-3 ml-2 flex-shrink-0" />
              </button>

              {/* Model Dropdown */}
              {showModelSelect && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded shadow-lg max-h-60 overflow-y-auto z-10">
                  {serverStatus.loadedModels.length > 0 ? (
                    serverStatus.loadedModels.map((model) => (
                      <button
                        key={model}
                        onClick={() => {
                          setSelectedModel(model)
                          setShowModelSelect(false)
                        }}
                        className={`w-full px-3 py-2 text-left text-xs hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors ${
                          selectedModel === model
                            ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400'
                            : 'text-gray-700 dark:text-gray-300'
                        }`}
                      >
                        {model}
                      </button>
                    ))
                  ) : (
                    <div className="px-3 py-2 text-xs text-gray-500 dark:text-gray-400">
                      No models loaded
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center px-4">
                <Cloud className="w-12 h-12 mb-3 text-gray-300 dark:text-gray-600" />
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Start a conversation</p>
                <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">Ask anything, get instant answers</p>
              </div>
            ) : (
              messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[85%] px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed ${
                      msg.role === 'user'
                        ? 'bg-primary-500 text-white shadow-sm'
                        : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 border border-gray-200 dark:border-gray-700'
                    }`}
                  >
                    <div className="whitespace-pre-wrap break-words">{msg.content}</div>
                  </div>
                </div>
              ))
            )}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 py-3 rounded-2xl">
                  <div className="flex space-x-1.5">
                    <div className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/50">
            <div className="flex gap-2 mb-2">
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
                placeholder="Type a message..."
                className="flex-1 px-3.5 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700
                  bg-white dark:bg-gray-900 text-sm
                  placeholder:text-gray-400 dark:placeholder:text-gray-500
                  focus:outline-none focus:ring-2 focus:ring-primary-400 focus:border-transparent
                  transition-all"
                disabled={isLoading}
              />
              <button
                onClick={handleSubmit}
                disabled={!input.trim() || isLoading}
                className="px-4 py-2.5 bg-primary-500 text-white rounded-lg
                  hover:bg-primary-600 active:bg-primary-700
                  disabled:opacity-40 disabled:cursor-not-allowed
                  transition-all duration-150 shadow-sm hover:shadow flex items-center justify-center"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>

            {/* Action Buttons - Only show if relevant */}
            {(messages.length > 0 || currentFile) && (
              <div className="flex items-center gap-2 text-xs">
                {messages.length > 0 && (
                  <button
                    onClick={handlePortToMainChat}
                    className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md
                      hover:bg-gray-200 dark:hover:bg-gray-700
                      text-gray-600 dark:text-gray-400
                      transition-colors"
                  >
                    <Share2 className="w-3 h-3" />
                    <span>Port to Chat</span>
                  </button>
                )}

                {currentFile && (
                  <button
                    onClick={handleGenerateSQL}
                    className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md
                      hover:bg-gray-200 dark:hover:bg-gray-700
                      text-gray-600 dark:text-gray-400
                      transition-colors"
                  >
                    <Zap className="w-3 h-3" />
                    <span>SQL</span>
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
