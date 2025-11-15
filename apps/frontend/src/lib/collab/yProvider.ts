/**
 * Yjs WebSocket Provider
 *
 * Connects Y.Doc to backend WebSocket for real-time synchronization.
 * Handles authentication, reconnection, and offline resilience.
 */

import * as Y from 'yjs'
import { WebsocketProvider } from 'y-websocket'

// Provider cache
const providers = new Map<string, WebsocketProvider>()

// WebSocket URL configuration
const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
const WS_HOST = window.location.hostname
const WS_PORT = import.meta.env.VITE_API_PORT || '8000'
const WS_BASE_URL = `${WS_PROTOCOL}//${WS_HOST}:${WS_PORT}`

/**
 * Create WebSocket provider for Y.Doc
 *
 * @param docId - Document UUID
 * @param ydoc - Y.Doc instance
 * @param token - JWT authentication token
 * @param onStatus - Callback for connection status changes
 * @returns WebsocketProvider instance
 */
export function createWebSocketProvider(
  docId: string,
  ydoc: Y.Doc,
  token: string,
  onStatus?: (status: 'connected' | 'disconnected' | 'synced') => void
): WebsocketProvider {
  // Return existing provider if cached
  if (providers.has(docId)) {
    return providers.get(docId)!
  }

  // Construct WebSocket URL with JWT token
  const wsUrl = `${WS_BASE_URL}/api/v1/collab/ws/${docId}?token=${encodeURIComponent(token)}`

  // Create provider
  const provider = new WebsocketProvider(wsUrl, docId, ydoc, {
    connect: true, // Auto-connect
    // WebSocket options
    WebSocketPolyfill: WebSocket,
    resyncInterval: 5000, // Resync every 5 seconds
    maxBackoffTime: 5000, // Max 5s reconnection backoff
  })

  // Status event handlers
  provider.on('status', ({ status }: { status: string }) => {
    console.log(`[YProvider] Status: ${status} (doc: ${docId})`)

    if (onStatus) {
      if (status === 'connected') {
        onStatus('connected')
      } else if (status === 'disconnected') {
        onStatus('disconnected')
      }
    }
  })

  provider.on('synced', ({ synced }: { synced: boolean }) => {
    if (synced) {
      console.log(`[YProvider] Synced: ${docId}`)
      onStatus?.('synced')
    }
  })

  provider.on('connection-error', (err: Error) => {
    console.error(`[YProvider] Connection error: ${err.message}`)
  })

  provider.on('connection-close', ({ code, reason }: { code: number; reason: string }) => {
    console.warn(`[YProvider] Connection closed: ${code} - ${reason}`)

    // Handle auth errors
    if (code === 1008) {
      console.error('[YProvider] Authentication failed - invalid or expired token')
      onStatus?.('disconnected')
    }
  })

  // Cache provider
  providers.set(docId, provider)

  return provider
}

/**
 * Disconnect and destroy WebSocket provider
 *
 * @param docId - Document UUID
 */
export function destroyWebSocketProvider(docId: string) {
  const provider = providers.get(docId)

  if (provider) {
    provider.disconnect()
    provider.destroy()
    providers.delete(docId)
    console.log(`[YProvider] Destroyed provider: ${docId}`)
  }
}

/**
 * Get connection status of a provider
 *
 * @param docId - Document UUID
 * @returns Connection status or null if provider doesn't exist
 */
export function getProviderStatus(docId: string): 'connected' | 'disconnected' | null {
  const provider = providers.get(docId)

  if (!provider) {
    return null
  }

  // Check WebSocket readyState
  if (provider.wsconnected) {
    return 'connected'
  }

  return 'disconnected'
}

/**
 * Manually trigger sync for a provider
 *
 * @param docId - Document UUID
 */
export function syncProvider(docId: string) {
  const provider = providers.get(docId)

  if (provider) {
    provider.connect()
    console.log(`[YProvider] Manual sync triggered: ${docId}`)
  }
}

/**
 * Disconnect all providers (useful for logout)
 */
export function disconnectAllProviders() {
  for (const [docId, provider] of providers.entries()) {
    provider.disconnect()
    provider.destroy()
  }
  providers.clear()

  console.log('[YProvider] Disconnected all providers')
}
