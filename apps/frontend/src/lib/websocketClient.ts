/**
 * WebSocket Client for Real-Time Vault Updates
 *
 * Handles WebSocket connections to receive real-time notifications
 * about file uploads, deletions, renames, and other vault activities.
 */

export interface WebSocketMessage {
  type: string
  [key: string]: any
}

export interface FileEvent {
  type: 'file_event'
  event: 'file_uploaded' | 'file_deleted' | 'file_renamed' | 'file_moved'
  file: any
  vault_type: string
  user_id: string
  timestamp: string
}

export interface UserPresenceEvent {
  type: 'user_presence'
  user_id: string
  status: 'online' | 'offline'
  timestamp: string
}

export interface ActivityEvent {
  type: 'activity'
  action: string
  resource_type: string
  details: string
  vault_type: string
  user_id: string
  timestamp: string
}

export type VaultWebSocketEvent = FileEvent | UserPresenceEvent | ActivityEvent

class VaultWebSocketClient {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000 // Start with 1 second
  private pingInterval: NodeJS.Timeout | null = null
  private listeners: Map<string, Set<(data: any) => void>> = new Map()
  private userId: string = 'default_user'
  private vaultType: string = 'real'
  private isConnecting = false

  connect(userId: string = 'default_user', vaultType: string = 'real') {
    if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
      console.log('WebSocket already connected or connecting')
      return
    }

    this.isConnecting = true
    this.userId = userId
    this.vaultType = vaultType

    // Get JWT token from localStorage
    const token = localStorage.getItem('auth_token')
    if (!token) {
      console.error('No auth token found - WebSocket connection requires authentication')
      this.isConnecting = false
      return
    }

    // Construct WebSocket URL with JWT token in query param
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.hostname
    const port = '8742' // Backend port
    const wsUrl = `${protocol}//${host}:${port}/api/v1/vault/ws/${userId}?vault_type=${vaultType}&token=${encodeURIComponent(token)}`

    console.log(`Connecting to WebSocket: ${wsUrl}`)

    try {
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.isConnecting = false
        this.reconnectAttempts = 0
        this.reconnectDelay = 1000

        // Start ping/keepalive
        this.startPing()

        // Notify listeners of connection
        this.emit('connected', { timestamp: new Date().toISOString() })
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log('WebSocket message received:', data)

          // Emit to specific event listeners
          this.emit(data.type, data)

          // Emit to general message listeners
          this.emit('message', data)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.emit('error', error)
      }

      this.ws.onclose = () => {
        console.log('WebSocket disconnected')
        this.isConnecting = false
        this.stopPing()
        this.emit('disconnected', { timestamp: new Date().toISOString() })

        // Attempt reconnection
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++
          const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1) // Exponential backoff
          console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`)

          setTimeout(() => {
            this.connect(this.userId, this.vaultType)
          }, delay)
        } else {
          console.error('Max reconnection attempts reached')
          this.emit('reconnect_failed', { attempts: this.reconnectAttempts })
        }
      }
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
      this.isConnecting = false
      this.emit('error', error)
    }
  }

  disconnect() {
    if (this.ws) {
      this.stopPing()
      this.ws.close()
      this.ws = null
    }
    this.reconnectAttempts = this.maxReconnectAttempts // Prevent reconnection
  }

  send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      console.warn('WebSocket not connected, cannot send message')
    }
  }

  on(event: string, callback: (data: any) => void) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event)!.add(callback)
  }

  off(event: string, callback: (data: any) => void) {
    const eventListeners = this.listeners.get(event)
    if (eventListeners) {
      eventListeners.delete(callback)
    }
  }

  private emit(event: string, data: any) {
    const eventListeners = this.listeners.get(event)
    if (eventListeners) {
      eventListeners.forEach(callback => {
        try {
          callback(data)
        } catch (error) {
          console.error(`Error in event listener for ${event}:`, error)
        }
      })
    }
  }

  private startPing() {
    this.stopPing()
    this.pingInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping' })
      }
    }, 30000) // Ping every 30 seconds
  }

  private stopPing() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }

  getConnectionState(): string {
    if (!this.ws) return 'disconnected'
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING: return 'connecting'
      case WebSocket.OPEN: return 'connected'
      case WebSocket.CLOSING: return 'closing'
      case WebSocket.CLOSED: return 'disconnected'
      default: return 'unknown'
    }
  }
}

// Export singleton instance
export const vaultWebSocket = new VaultWebSocketClient()
