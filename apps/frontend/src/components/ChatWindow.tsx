import { useEffect, useRef, useState } from 'react'
import { Settings, AlertTriangle } from 'lucide-react'
import { ChatMessage } from './ChatMessage'
import { ChatInput } from './ChatInput'
import { ModelSelector } from './ModelSelector'
import { TokenMeter } from './TokenMeter'
import { useChatStore } from '../stores/chatStore'
import { api } from '../lib/api'
import { shallow } from 'zustand/shallow'  // MED-03: Prevent unnecessary re-renders
import { showToast, showActionToast } from '../lib/toast'

export function ChatWindow() {
  // MED-03: Use shallow selector to only re-render when used fields change
  const {
    activeChatId,
    messages,
    streamingContent,
    isSending,
    settings,
    getActiveSession,
    addMessage,
    setStreamingContent,
    appendStreamingContent,
    clearStreamingContent,
    setIsSending,
    createSession,
    setActiveChat
  } = useChatStore(
    (state) => ({
      activeChatId: state.activeChatId,
      messages: state.messages,
      streamingContent: state.streamingContent,
      isSending: state.isSending,
      settings: state.settings,
      getActiveSession: state.getActiveSession,
      addMessage: state.addMessage,
      setStreamingContent: state.setStreamingContent,
      appendStreamingContent: state.appendStreamingContent,
      clearStreamingContent: state.clearStreamingContent,
      setIsSending: state.setIsSending,
      createSession: state.createSession,
      setActiveChat: state.setActiveChat,
    }),
    shallow
  )

  const [selectedModel, setSelectedModel] = useState<string>('')
  const [ollamaHealth, setOllamaHealth] = useState<{status: string, message: string} | null>(null)
  const [pendingSummarize, setPendingSummarize] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  const activeSession = getActiveSession()

  // Set initial model from session
  useEffect(() => {
    if (activeSession?.model) {
      setSelectedModel(activeSession.model)
    }
  }, [activeSession])

  // Persist model selection to session (with optimistic update)
  const handleModelChange = async (model: string) => {
    if (!activeChatId) return

    const previousModel = selectedModel

    // Optimistic update
    setSelectedModel(model)

    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch(`/api/v1/chat/sessions/${activeChatId}/model`, {
        method: 'PATCH',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ model })
      })

      if (!response.ok) {
        // Revert on failure
        setSelectedModel(previousModel)
        showToast.error('Failed to save model selection')
        console.error('Failed to persist model selection')
      }
    } catch (error) {
      // Revert on error
      setSelectedModel(previousModel)
      showToast.error('Network error - model selection not saved')
      console.error('Error persisting model:', error)
    }
  }

  // Handle summarization request
  const handleSummarize = () => {
    setPendingSummarize(true)
    showToast.success('Next message will include context summarization', 4000)
  }

  // Handle near-limit warning
  const handleNearLimit = () => {
    showActionToast(
      'Approaching context limit — summarize or start fresh?',
      'Summarize Context',
      handleSummarize,
      { type: 'warning', duration: 10000 }
    )
  }

  // Check Ollama health on mount and periodically
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await api.get('/v1/chat/health')
        setOllamaHealth(response.data)
      } catch (error) {
        // Don't show error banner - Ollama is managed by startup script
        console.debug('Ollama health check failed:', error)
      }
    }

    checkHealth()
    const interval = setInterval(checkHealth, 30000) // Check every 30s

    return () => clearInterval(interval)
  }, [])

  // Auto-scroll to bottom when messages update (instant, no animation)
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'instant' })
  }, [messages, streamingContent])

  // Cleanup EventSource on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])


  const handleSendMessage = async (content: string, files?: File[]) => {
    if (!activeChatId) return

    setIsSending(true)

    try {
      // Upload files first if any
      const uploadedFiles = []
      if (files && files.length > 0) {
        for (const file of files) {
          const formData = new FormData()
          formData.append('file', file)

          const uploadResponse = await fetch(
            `/api/v1/chat/sessions/${activeChatId}/upload`,
            {
              method: 'POST',
              body: formData
            }
          )

          if (uploadResponse.ok) {
            const fileInfo = await uploadResponse.json()
            uploadedFiles.push(fileInfo)
          }
        }
      }

      // Add user message to UI
      const userMessage = {
        role: 'user' as const,
        content,
        timestamp: new Date().toISOString(),
        files: uploadedFiles
      }
      addMessage(userMessage)

      // Prepare system prompt with optional summarization instruction
      let effectiveSystemPrompt = settings.systemPrompt || undefined
      if (pendingSummarize) {
        const summarizeInstruction = '\n\nIMPORTANT: Before responding, briefly summarize the key points from our previous conversation to compress context, then answer the current question.'
        effectiveSystemPrompt = (effectiveSystemPrompt || '') + summarizeInstruction
        setPendingSummarize(false) // Clear flag after use
      }

      // Send message via SSE with LLM parameters (with safe defaults)
      const response = await fetch(
        `/api/v1/chat/sessions/${activeChatId}/messages`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            content,
            model: selectedModel || activeSession?.model,
            temperature: settings.temperature ?? 0.7,
            top_p: settings.topP ?? 0.9,
            top_k: settings.topK ?? 40,
            repeat_penalty: settings.repeatPenalty ?? 1.1,
            system_prompt: effectiveSystemPrompt
          })
        }
      )

      if (!response.ok) {
        throw new Error('Failed to send message')
      }

      // Handle SSE stream
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        throw new Error('No response body')
      }

      clearStreamingContent()
      let fullResponse = ''
      let pendingContent = ''
      let animationFrameId: number | null = null

      // Smooth streaming with requestAnimationFrame throttling
      const flushPendingContent = () => {
        if (pendingContent) {
          appendStreamingContent(pendingContent)
          pendingContent = ''
        }
        animationFrameId = null
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          // Flush any remaining content
          if (animationFrameId) {
            cancelAnimationFrame(animationFrameId)
          }
          flushPendingContent()
          break
        }

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (!line.trim() || !line.startsWith('data: ')) continue

          const data = line.replace('data: ', '').trim()
          if (data === '[START]') continue

          try {
            const parsed = JSON.parse(data)

            if (parsed.content) {
              fullResponse += parsed.content
              pendingContent += parsed.content

              // Throttle updates to 60fps using requestAnimationFrame
              if (!animationFrameId) {
                animationFrameId = requestAnimationFrame(flushPendingContent)
              }
            }

            if (parsed.done) {
              // Add complete assistant message
              const assistantMessage = {
                role: 'assistant' as const,
                content: fullResponse,
                timestamp: new Date().toISOString(),
                model: selectedModel || activeSession?.model,
                tokens: fullResponse.split(/\s+/).length
              }
              addMessage(assistantMessage)
              clearStreamingContent()
            }

            if (parsed.error) {
              console.error('Streaming error:', parsed.error)
            }
          } catch (e) {
            // Not JSON, ignore
          }
        }
      }
    } catch (error) {
      console.error('Failed to send message:', error)
      alert('Failed to send message. Make sure Ollama is running.')
    } finally {
      setIsSending(false)
    }
  }

  if (!activeChatId) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
        <div className="text-center">
          <Settings size={64} className="mx-auto mb-4 opacity-50" />
          <p className="text-lg font-medium">No chat selected</p>
          <p className="text-sm mt-2">Select a chat or create a new one</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col glass-panel relative overflow-hidden">
      {/* Background gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary-50/30 via-transparent to-blue-50/20 dark:from-primary-900/10 dark:via-transparent dark:to-blue-900/5 pointer-events-none" />
      {/* Ollama Warning Banner */}
      {ollamaHealth?.status === 'unhealthy' && (
        <div className="relative flex-shrink-0 px-4 py-3 bg-orange-100 dark:bg-orange-900/30 border-b border-orange-200 dark:border-orange-800">
          <div className="flex items-center gap-3">
            <AlertTriangle size={20} className="text-orange-600 dark:text-orange-400 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium text-orange-900 dark:text-orange-100">
                {ollamaHealth.message}
              </p>
              <p className="text-xs text-orange-700 dark:text-orange-300 mt-1">
                Start Ollama with: <code className="px-1 py-0.5 bg-orange-200 dark:bg-orange-800 rounded">ollama serve</code>
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="relative flex-shrink-0 px-4 py-3 border-b border-white/10 dark:border-gray-700/30 flex items-center justify-between backdrop-blur-sm bg-white/50 dark:bg-gray-900/50">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {activeSession?.title || 'Chat'}
          </h2>
          <div className="flex items-center gap-3">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {messages.length} messages
            </p>
            {activeChatId && (
              <TokenMeter
                sessionId={activeChatId}
                refreshOn={messages.length}
                onNearLimit={handleNearLimit}
              />
            )}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <ModelSelector value={selectedModel} onChange={handleModelChange} />
        </div>
      </div>

      {/* Messages */}
      <div className="relative flex-1 overflow-y-auto px-6 py-4 scrollbar-thin">
        {messages.length === 0 && !streamingContent ? (
          <div className="h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
            <div className="text-center max-w-md">
              <p className="text-lg font-medium mb-2">Start a conversation</p>
              <p className="text-sm">
                Ask me anything! I can help with code, answer questions, or just chat.
              </p>
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, index) => (
              <ChatMessage key={index} message={msg} />
            ))}

            {/* Streaming message */}
            {streamingContent && (
              <ChatMessage
                message={{
                  role: 'assistant',
                  content: streamingContent,
                  timestamp: new Date().toISOString(),
                  model: selectedModel || activeSession?.model
                }}
                isStreaming={true}
              />
            )}

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input */}
      <div className="relative flex-shrink-0">
        <ChatInput
          onSend={handleSendMessage}
          disabled={isSending}
          placeholder={
            isSending ? 'Sending...' : 'Type a message...'
          }
        />
      </div>

    </div>
  )
}
