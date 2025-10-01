import { useEffect, useRef, useState } from 'react'
import { Settings } from 'lucide-react'
import { ChatMessage } from './ChatMessage'
import { ChatInput } from './ChatInput'
import { ModelSelector } from './ModelSelector'
import { useChatStore } from '../stores/chatStore'
import { api } from '../lib/api'

export function ChatWindow() {
  const {
    activeChatId,
    messages,
    streamingContent,
    isSending,
    getActiveSession,
    addMessage,
    setStreamingContent,
    appendStreamingContent,
    clearStreamingContent,
    setIsSending
  } = useChatStore()

  const [selectedModel, setSelectedModel] = useState<string>('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  const activeSession = getActiveSession()

  // Set initial model from session
  useEffect(() => {
    if (activeSession?.model) {
      setSelectedModel(activeSession.model)
    }
  }, [activeSession])

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
            `${api.BASE_URL}/api/v1/chat/sessions/${activeChatId}/upload`,
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

      // Send message via SSE
      const response = await fetch(
        `${api.BASE_URL}/api/v1/chat/sessions/${activeChatId}/messages`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            content,
            model: selectedModel || activeSession?.model
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

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

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
              appendStreamingContent(parsed.content)
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
    <div className="h-full flex flex-col glass-panel">
      {/* Header */}
      <div className="flex-shrink-0 px-6 py-4 border-b border-white/10 dark:border-gray-700/30 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {activeSession?.title || 'Chat'}
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {messages.length} messages
          </p>
        </div>

        <ModelSelector value={selectedModel} onChange={setSelectedModel} />
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 scrollbar-thin">
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
      <div className="flex-shrink-0">
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
