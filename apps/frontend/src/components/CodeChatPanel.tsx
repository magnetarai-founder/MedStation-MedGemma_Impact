/**
 * CodeChatPanel - Chat interface for Code Tab with project context awareness
 * Reuses ChatWindow component with modified toolbar for code-specific actions
 */

import { useEffect, useRef, useState } from 'react'
import { XCircle, Eraser, MessageSquarePlus, Loader2 } from 'lucide-react'
import { ChatMessage } from './ChatMessage'
import { ChatInput } from './ChatInput'
import { ModelSelector } from './ModelSelector'
import { useChatStore } from '../stores/chatStore'
import { useEditorStore } from '../stores/editorStore'
import { api } from '../lib/api'

export function CodeChatPanel() {
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
    setIsSending
  } = useChatStore()

  const { code } = useEditorStore() // Access to current code in editor
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

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  const handleSend = async (message: string) => {
    if (!message.trim() || isSending) return

    try {
      setIsSending(true)

      // Add user message
      addMessage({
        role: 'user',
        content: message,
      })

      // Include current code as context in the message
      const contextMessage = code.trim()
        ? `Current file context:\n\`\`\`\n${code}\n\`\`\`\n\nUser message: ${message}`
        : message

      // Send to backend with streaming
      const response = await fetch('/api/v1/chat/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chat_id: activeChatId,
          message: contextMessage,
          model: selectedModel,
          stream: true,
        })
      })

      if (!response.ok) throw new Error('Failed to send message')

      // Handle streaming response
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let fullContent = ''

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6)
              if (data === '[DONE]') continue

              try {
                const parsed = JSON.parse(data)
                if (parsed.content) {
                  fullContent += parsed.content
                  setStreamingContent(fullContent)
                }
              } catch (e) {
                // Skip invalid JSON
              }
            }
          }
        }
      }

      // Add assistant message when done
      if (fullContent) {
        addMessage({
          role: 'assistant',
          content: fullContent,
        })
      }
      clearStreamingContent()

    } catch (error) {
      console.error('Error sending message:', error)
      addMessage({
        role: 'assistant',
        content: 'Sorry, there was an error processing your message.',
      })
    } finally {
      setIsSending(false)
    }
  }

  const handleEject = () => {
    if (window.confirm('Eject current chat session? This will create a new session.')) {
      // TODO: Implement eject/disconnect logic
      console.log('Eject clicked')
    }
  }

  const handleClearChat = () => {
    if (window.confirm('Clear all messages in this chat?')) {
      // Clear messages for current session
      // TODO: Implement clear chat logic
      console.log('Clear chat clicked')
    }
  }

  const handleCodeWithAI = () => {
    // TODO: Implement "Code with AI" action - could auto-insert a helpful prompt
    console.log('Code with AI clicked')
  }

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar - Modified from Database tab's ResultsTable */}
      <div className="flex items-center px-2 py-2 border-b-2 border-gray-600 dark:border-gray-400">
        <div className="flex items-center gap-3">
          {/* Model Selector */}
          <ModelSelector
            value={selectedModel}
            onChange={setSelectedModel}
          />

          {/* Group 2: Eject - only enabled if model is loaded */}
          <div className="flex items-center px-1.5 py-0.5 rounded-md bg-gray-100/50 dark:bg-gray-800/50">
            <button
              onClick={handleEject}
              disabled={!selectedModel}
              className={`p-1 rounded ${
                selectedModel
                  ? 'hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
                  : 'opacity-40 cursor-not-allowed text-gray-400 dark:text-gray-600'
              }`}
              title={selectedModel ? "Eject model" : "No model loaded"}
            >
              <XCircle className="w-4 h-4" />
            </button>
          </div>

          {/* Group 3: Clear (Eraser) */}
          <div className="flex items-center px-1.5 py-0.5 rounded-md bg-gray-100/50 dark:bg-gray-800/50">
            <button
              onClick={handleClearChat}
              disabled={messages.length === 0}
              className={`p-1 rounded ${
                messages.length === 0
                  ? 'opacity-40 cursor-not-allowed text-gray-400 dark:text-gray-600'
                  : 'hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
              }`}
              title={messages.length === 0 ? 'No messages to clear' : 'Clear chat'}
            >
              <Eraser className="w-4 h-4" />
            </button>
          </div>

          {/* Group 4: Code with AI */}
          <div className="flex items-center px-1.5 py-0.5 rounded-md bg-gray-100/50 dark:bg-gray-800/50">
            <button
              onClick={handleCodeWithAI}
              className="flex items-center gap-1.5 px-3 py-0.5 text-xs font-medium rounded hover:bg-primary-100 dark:hover:bg-primary-900/30 text-primary-700 dark:text-primary-400"
              title="Get AI coding assistance"
            >
              <MessageSquarePlus className="w-3.5 h-3.5" />
              <span>Code with AI</span>
            </button>
          </div>
        </div>
      </div>

      {/* Chat Messages Area */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {messages.length === 0 && !streamingContent && (
          <div className="flex h-full items-center justify-center">
            <div className="text-center text-gray-500">
              <MessageSquarePlus className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>Start a conversation about your code</p>
              <p className="text-sm mt-1">The AI has context of your entire project</p>
            </div>
          </div>
        )}

        {messages.map((message, index) => (
          <ChatMessage key={index} message={message} />
        ))}

        {streamingContent && (
          <ChatMessage
            message={{
              role: 'assistant',
              content: streamingContent,
            }}
          />
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Chat Input */}
      <div className="border-t border-gray-200 dark:border-gray-700">
        <ChatInput
          onSend={handleSend}
          disabled={isSending}
          placeholder="Ask about your code..."
        />
      </div>
    </div>
  )
}
