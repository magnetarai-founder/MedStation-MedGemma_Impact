import * as Y from 'yjs'
import { WebsocketProvider } from 'y-websocket'
import { IndexeddbPersistence } from 'y-indexeddb'

/**
 * Create a WebSocket provider for a Yjs document.
 *
 * Connects to the existing collab WebSocket endpoint: /api/v1/collab/ws/{doc_id}
 *
 * @param docId Document identifier (e.g., "board:abc123" or "wiki:xyz789")
 * @param ydoc Y.Doc instance
 * @returns WebsocketProvider instance
 */
export function getProviderForDoc(docId: string, ydoc: Y.Doc): WebsocketProvider {
  // Determine WebSocket URL
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const wsUrl = `${protocol}//${host}/api/v1/collab/ws/${docId}`

  // Get auth token from localStorage
  const token = localStorage.getItem('auth_token')

  // Create provider with auth token in URL params
  const provider = new WebsocketProvider(
    wsUrl,
    docId,
    ydoc,
    {
      params: token ? { token } : {},
      connect: true
    }
  )

  return provider
}

/**
 * Create an IndexedDB persistence layer for offline support.
 *
 * @param docId Document identifier
 * @param ydoc Y.Doc instance
 * @returns IndexeddbPersistence instance
 */
export function getIndexedDBProvider(docId: string, ydoc: Y.Doc): IndexeddbPersistence {
  return new IndexeddbPersistence(docId, ydoc)
}

/**
 * Create both WebSocket and IndexedDB providers for full offline-first support.
 *
 * @param docId Document identifier
 * @param ydoc Y.Doc instance
 * @returns Object with both providers
 */
export function createProviders(docId: string, ydoc: Y.Doc) {
  const wsProvider = getProviderForDoc(docId, ydoc)
  const idbProvider = getIndexedDBProvider(docId, ydoc)

  return {
    wsProvider,
    idbProvider,
    destroy: () => {
      wsProvider.destroy()
      idbProvider.destroy()
    }
  }
}
