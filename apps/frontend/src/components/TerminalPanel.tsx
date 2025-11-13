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
  const wsRef = useRef<WebSocket | null>(null)
  const outputRef = useRef<HTMLPreElement>(null)

  useEffect(() => {
    if (!isOpen) return

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

        // Prefer absolute or relative ws URL from backend; fallback to relative path
        const wsUrl = data.websocket_url.startsWith('ws')
          ? data.websocket_url
          : (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + data.websocket_url

        const ws = new WebSocket(wsUrl)
        wsRef.current = ws

        ws.onmessage = (evt) => {
          // Expecting plaintext lines; if JSON, adjust accordingly
          setOutput((prev) => prev + (typeof evt.data === 'string' ? evt.data : ''))
        }
        ws.onerror = () => setError('WebSocket connection error')
        ws.onclose = () => setOutput((prev) => prev + '\n[Terminal closed]')
      } catch (e: any) {
        setError(e?.message || 'Failed to start terminal')
      }
    }

    spawnTerminal()
    return () => {
      if (wsRef.current) wsRef.current.close()
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
            />
            <button onClick={sendCommand} className="px-4 py-1.5 bg-primary-600 text-white rounded text-sm">
              Send
            </button>
          </div>
        </>
      )}
    </div>
  )
}
