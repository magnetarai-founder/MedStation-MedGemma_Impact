import React, { useEffect, useRef, useState } from 'react'
import { Terminal as TerminalIcon, X } from 'lucide-react'

interface TerminalPanelProps {
  isOpen: boolean
  onClose: () => void
}

export function TerminalPanel({ isOpen, onClose }: TerminalPanelProps) {
  const [terminalId, setTerminalId] = useState<string | null>(null)
  const [output, setOutput] = useState<string>('')
  const [input, setInput] = useState<string>('')
  const [error, setError] = useState<string | null>(null)
  const [reconnecting, setReconnecting] = useState<boolean>(false)
  const wsRef = useRef<WebSocket | null>(null)
  const outputRef = useRef<HTMLPreElement>(null)
  const reconnectAttemptsRef = useRef<number>(0)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const isClosingRef = useRef<boolean>(false)

  const MAX_RECONNECT_ATTEMPTS = 5
  const BACKOFF_DELAYS = [1000, 2000, 4000, 8000, 16000] // 1s, 2s, 4s, 8s, 16s

  useEffect(() => {
    if (!isOpen) {
      // User closed panel - stop reconnecting
      isClosingRef.current = true
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
      return
    }

    isClosingRef.current = false
    reconnectAttemptsRef.current = 0

    const spawnTerminal = async () => {
      try {
        const res = await fetch('/api/v1/terminal/spawn', { method: 'POST', credentials: 'include' })
        if (!res.ok) {
          if (res.status === 403) {
            setError('Permission denied: code.terminal required')
            return
          }
          throw new Error(`Failed to spawn terminal (${res.status})`)
        }
        const data = await res.json()
        setTerminalId(data.terminal_id)

        connectWebSocket(data.websocket_url)
      } catch (e: any) {
        setError(e?.message || 'Failed to start terminal')
      }
    }

    const connectWebSocket = (websocketUrl: string) => {
      // Prefer absolute or relative ws URL from backend; fallback to relative path
      const wsUrl = websocketUrl.startsWith('ws')
        ? websocketUrl
        : (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + websocketUrl

      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        setReconnecting(false)
        reconnectAttemptsRef.current = 0
        setError(null)
      }

      ws.onmessage = (evt) => {
        // Expecting plaintext lines; if JSON, adjust accordingly
        setOutput((prev) => prev + (typeof evt.data === 'string' ? evt.data : ''))
      }

      ws.onerror = () => {
        if (!isClosingRef.current) {
          setError('WebSocket connection error')
        }
      }

      ws.onclose = () => {
        if (isClosingRef.current) {
          // User intentionally closed - don't reconnect
          setOutput((prev) => prev + '\n[Terminal closed]')
          return
        }

        // Unexpected close - attempt reconnect
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          const delay = BACKOFF_DELAYS[reconnectAttemptsRef.current] || 30000
          setReconnecting(true)
          setOutput((prev) => prev + `\n[Connection lost. Reconnecting in ${delay / 1000}s... (${reconnectAttemptsRef.current + 1}/${MAX_RECONNECT_ATTEMPTS})]`)

          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current += 1
            connectWebSocket(websocketUrl)
          }, delay)
        } else {
          setError(`Connection failed after ${MAX_RECONNECT_ATTEMPTS} attempts`)
          setReconnecting(false)
          setOutput((prev) => prev + '\n[Terminal disconnected - maximum reconnect attempts reached]')
        }
      }
    }

    spawnTerminal()

    return () => {
      isClosingRef.current = true
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [isOpen])

  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight
    }
  }, [output])

  const sendCommand = () => {
    if (!wsRef.current || !input.trim()) return
    // Send as plaintext with newline
    wsRef.current.send(input + '\n')
    setInput('')
  }

  if (!isOpen) return null

  return (
    <div className="border-t border-gray-200 dark:border-gray-700 bg-gray-900 text-gray-100">
      <div className="px-4 py-2 border-b border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TerminalIcon className="w-4 h-4" />
          <span className="text-sm font-medium">Terminal</span>
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-200">
          <X className="w-4 h-4" />
        </button>
      </div>

      {error ? (
        <div className="p-4 text-sm text-red-400">{error}</div>
      ) : (
        <>
          {reconnecting && (
            <div className="px-4 py-2 bg-yellow-900/20 border-b border-yellow-700 text-yellow-400 text-xs">
              Reconnecting...
            </div>
          )}
          <pre ref={outputRef} className="h-64 overflow-auto p-4 text-xs font-mono">
            {output || 'Connecting...'}
          </pre>
          <div className="p-2 border-t border-gray-700 flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendCommand()}
              placeholder="Type command..."
              className="flex-1 px-3 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm"
              disabled={reconnecting || !!error}
            />
            <button
              onClick={sendCommand}
              className="px-4 py-1.5 bg-primary-600 text-white rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={reconnecting || !!error}
            >
              Send
            </button>
          </div>
        </>
      )}
    </div>
  )
}
