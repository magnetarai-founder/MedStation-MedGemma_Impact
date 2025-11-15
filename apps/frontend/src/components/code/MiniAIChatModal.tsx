import { useEffect, useRef, useState } from 'react'
import { X, SendHorizonal } from 'lucide-react'

interface MiniAIChatModalProps {
  isOpen: boolean
  onClose: () => void
  context: { filePath?: string; language?: string }
}

type ChatMsg = { role: 'user' | 'assistant' | 'system'; content: string }

export function MiniAIChatModal({ isOpen, onClose, context }: MiniAIChatModalProps) {
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement | null>(null)

  useEffect(() => {
    if (!isOpen) return
    // Seed a small system prompt with file context
    const header = `Coding context:\n- File: ${context.filePath || '(none)'}\n- Language: ${context.language || 'plaintext'}`
    setMessages([{ role: 'system', content: header }])
    setInput('')
    setBusy(false)
    // Focus input
    setTimeout(() => inputRef.current?.focus(), 50)
  }, [isOpen, context.filePath, context.language])

  const send = async () => {
    const content = input.trim()
    if (!content) return
    setMessages((prev) => [...prev, { role: 'user', content }])
    setInput('')
    setBusy(true)
    try {
      // TODO: Integrate with your chat API endpoint, passing file context and prompt
      // Placeholder: echo back a canned assistant reply
      await new Promise((r) => setTimeout(r, 400))
      setMessages((prev) => [...prev, { role: 'assistant', content: 'Here is a suggested change based on your question. (Placeholder)' }])
    } catch {
      // noop
    } finally {
      setBusy(false)
    }
  }

  if (!isOpen) return null
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-end pointer-events-none">
      {/* Window */}
      <div className="m-4 w-[420px] max-w-[90vw] h-[520px] rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 flex flex-col pointer-events-auto">
        {/* Header */}
        <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <div className="text-sm font-medium">Mini AI Assistant</div>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800" aria-label="Close">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-auto p-3 text-sm space-y-2">
          {messages.map((m, i) => (
            <div key={i} className={m.role === 'assistant' ? 'text-gray-800 dark:text-gray-200' : m.role === 'system' ? 'text-gray-500' : ''}>
              {m.role === 'user' && <div className="text-xs text-blue-600 dark:text-blue-400 mb-0.5">You</div>}
              {m.role === 'assistant' && <div className="text-xs text-emerald-600 dark:text-emerald-400 mb-0.5">Assistant</div>}
              <div className="whitespace-pre-wrap">{m.content}</div>
            </div>
          ))}
        </div>

        {/* Composer */}
        <div className="border-t border-gray-200 dark:border-gray-700 p-2">
          <div className="flex items-end gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              rows={2}
              placeholder="Ask the AI about this file…"
              className="flex-1 rounded border px-2 py-1 text-sm bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-700"
            />
            <button
              onClick={send}
              disabled={busy || !input.trim()}
              className="px-2.5 py-1.5 rounded text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
            >
              <SendHorizonal className="w-4 h-4" />
              <span>Send</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

