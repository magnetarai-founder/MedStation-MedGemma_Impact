/**
 * TerminalView - Real-time terminal with xterm.js
 *
 * Features:
 * - WebSocket connection to backend PTY
 * - Full terminal emulation with xterm.js
 * - Auto-resize support
 * - Command history and context capture
 */

import { useEffect, useRef, useState } from 'react'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import { WebLinksAddon } from 'xterm-addon-web-links'
import 'xterm/css/xterm.css'
import { X, Maximize2, Minimize2 } from 'lucide-react'
import toast from 'react-hot-toast'

interface TerminalViewProps {
  terminalId?: string
  onClose?: () => void
  autoSpawn?: boolean
  shell?: string
  cwd?: string
}

export function TerminalView({
  terminalId: initialTerminalId,
  onClose,
  autoSpawn = true,
  shell,
  cwd
}: TerminalViewProps) {
  const terminalRef = useRef<HTMLDivElement>(null)
  const xtermRef = useRef<Terminal | null>(null)
  const fitAddonRef = useRef<FitAddon | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const [terminalId, setTerminalId] = useState<string | null>(initialTerminalId || null)
  const [isConnected, setIsConnected] = useState(false)
  const [isMaximized, setIsMaximized] = useState(false)

  // Spawn terminal session
  const spawnTerminal = async () => {
    try {
      const params = new URLSearchParams()
      if (shell) params.append('shell', shell)
      if (cwd) params.append('cwd', cwd)

      const response = await fetch(`/api/v1/terminal/spawn?${params}`, {
        method: 'POST',
        credentials: 'include'
      })

      if (!response.ok) {
        throw new Error('Failed to spawn terminal')
      }

      const data = await response.json()
      setTerminalId(data.terminal_id)
      return data.terminal_id

    } catch (error) {
      console.error('Error spawning terminal:', error)
      toast.error('Failed to spawn terminal')
      return null
    }
  }

  // Initialize xterm.js terminal
  useEffect(() => {
    if (!terminalRef.current) return

    // Create terminal instance
    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      theme: {
        background: '#1e1e1e',
        foreground: '#d4d4d4',
        cursor: '#ffffff',
        black: '#000000',
        red: '#cd3131',
        green: '#0dbc79',
        yellow: '#e5e510',
        blue: '#2472c8',
        magenta: '#bc3fbc',
        cyan: '#11a8cd',
        white: '#e5e5e5',
        brightBlack: '#666666',
        brightRed: '#f14c4c',
        brightGreen: '#23d18b',
        brightYellow: '#f5f543',
        brightBlue: '#3b8eea',
        brightMagenta: '#d670d6',
        brightCyan: '#29b8db',
        brightWhite: '#e5e5e5'
      },
      scrollback: 10000,
      allowProposedApi: true
    })

    // Add fit addon
    const fitAddon = new FitAddon()
    term.loadAddon(fitAddon)

    // Add web links addon
    const webLinksAddon = new WebLinksAddon()
    term.loadAddon(webLinksAddon)

    // Open terminal in DOM
    term.open(terminalRef.current)

    // Fit to container
    fitAddon.fit()

    // Store refs
    xtermRef.current = term
    fitAddonRef.current = fitAddon

    // Handle resize
    const handleResize = () => {
      if (fitAddonRef.current && xtermRef.current) {
        fitAddonRef.current.fit()

        // Send resize to backend
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN && terminalId) {
          wsRef.current.send(JSON.stringify({
            type: 'resize',
            rows: xtermRef.current.rows,
            cols: xtermRef.current.cols
          }))
        }
      }
    }

    window.addEventListener('resize', handleResize)

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize)
      term.dispose()
    }
  }, [])

  // Connect to WebSocket when terminalId is available
  useEffect(() => {
    if (!terminalId || !xtermRef.current) return

    const term = xtermRef.current

    // WebSocket connection
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/v1/terminal/ws/${terminalId}`

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('Terminal WebSocket connected')
      setIsConnected(true)

      // Send initial resize
      if (fitAddonRef.current) {
        fitAddonRef.current.fit()
        ws.send(JSON.stringify({
          type: 'resize',
          rows: term.rows,
          cols: term.cols
        }))
      }
    }

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)

        if (message.type === 'output') {
          term.write(message.data)
        } else if (message.type === 'error') {
          console.error('Terminal error:', message.message)
          toast.error(message.message)
        }
      } catch (error) {
        // Not JSON, treat as raw output
        term.write(event.data)
      }
    }

    ws.onerror = (error) => {
      console.error('Terminal WebSocket error:', error)
      toast.error('Terminal connection error')
      setIsConnected(false)
    }

    ws.onclose = () => {
      console.log('Terminal WebSocket closed')
      setIsConnected(false)
    }

    // Handle terminal input
    const disposable = term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          type: 'input',
          data: data
        }))
      }
    })

    // Cleanup
    return () => {
      disposable.dispose()
      ws.close()
    }
  }, [terminalId])

  // Auto-spawn terminal on mount
  useEffect(() => {
    if (autoSpawn && !terminalId) {
      spawnTerminal()
    }
  }, [autoSpawn])

  // Handle close
  const handleClose = async () => {
    if (terminalId) {
      try {
        await fetch(`/api/v1/terminal/${terminalId}`, {
          method: 'DELETE',
          credentials: 'include'
        })
      } catch (error) {
        console.error('Error closing terminal:', error)
      }
    }

    if (onClose) {
      onClose()
    }
  }

  // Toggle maximize
  const toggleMaximize = () => {
    setIsMaximized(!isMaximized)
    // Re-fit after state change
    setTimeout(() => {
      if (fitAddonRef.current) {
        fitAddonRef.current.fit()
      }
    }, 100)
  }

  return (
    <div
      className={`flex flex-col bg-[#1e1e1e] ${
        isMaximized ? 'fixed inset-0 z-50' : 'h-full'
      }`}
    >
      {/* Terminal Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#2d2d2d] border-b border-gray-700">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm text-gray-400">
            Terminal {terminalId ? `(${terminalId.slice(0, 8)}...)` : ''}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={toggleMaximize}
            className="p-1 hover:bg-gray-700 rounded transition-colors"
            title={isMaximized ? 'Minimize' : 'Maximize'}
          >
            {isMaximized ? (
              <Minimize2 className="w-4 h-4 text-gray-400" />
            ) : (
              <Maximize2 className="w-4 h-4 text-gray-400" />
            )}
          </button>

          <button
            onClick={handleClose}
            className="p-1 hover:bg-red-600 rounded transition-colors"
            title="Close Terminal"
          >
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </div>
      </div>

      {/* Terminal Container */}
      <div
        ref={terminalRef}
        className="flex-1 p-2 overflow-hidden"
        style={{ minHeight: isMaximized ? 'calc(100vh - 48px)' : '400px' }}
      />

      {!isConnected && terminalId && (
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50">
          <div className="text-white text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto mb-2" />
            <p>Connecting to terminal...</p>
          </div>
        </div>
      )}
    </div>
  )
}
