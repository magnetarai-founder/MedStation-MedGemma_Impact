/**
 * Yjs Document Management
 *
 * Creates and manages Y.Doc instances with IndexedDB persistence.
 * Supports offline editing with automatic sync on reconnection.
 */

import * as Y from 'yjs'
import { IndexeddbPersistence } from 'y-indexeddb'

// In-memory cache of Y.Doc instances
const ydocs = new Map<string, Y.Doc>()
const persistenceProviders = new Map<string, IndexeddbPersistence>()

/**
 * Get or create Y.Doc for a document ID
 *
 * @param docId - Document UUID
 * @param enablePersistence - Enable IndexedDB persistence (default: true)
 * @returns Y.Doc instance
 */
export function getYDoc(docId: string, enablePersistence = true): Y.Doc {
  // Return existing doc if cached
  if (ydocs.has(docId)) {
    return ydocs.get(docId)!
  }

  // Create new Y.Doc
  const ydoc = new Y.Doc()
  ydocs.set(docId, ydoc)

  // Setup IndexedDB persistence
  if (enablePersistence) {
    const persistence = new IndexeddbPersistence(docId, ydoc)

    // Wait for persistence to sync
    persistence.on('synced', () => {
      console.log(`[YDoc] Synced from IndexedDB: ${docId}`)
    })

    persistenceProviders.set(docId, persistence)
  }

  console.log(`[YDoc] Created Y.Doc: ${docId}`)

  return ydoc
}

/**
 * Destroy Y.Doc and cleanup resources
 *
 * @param docId - Document UUID
 */
export function destroyYDoc(docId: string) {
  // Destroy persistence provider
  const persistence = persistenceProviders.get(docId)
  if (persistence) {
    persistence.destroy()
    persistenceProviders.delete(docId)
  }

  // Destroy Y.Doc
  const ydoc = ydocs.get(docId)
  if (ydoc) {
    ydoc.destroy()
    ydocs.delete(docId)
  }

  console.log(`[YDoc] Destroyed Y.Doc: ${docId}`)
}

/**
 * Get Y.Text instance for collaborative text editing
 *
 * @param ydoc - Y.Doc instance
 * @param key - Text field key (default: 'content')
 * @returns Y.Text instance
 */
export function getYText(ydoc: Y.Doc, key = 'content'): Y.Text {
  return ydoc.getText(key)
}

/**
 * Get Y.Array instance for grid docs (tables)
 *
 * @param ydoc - Y.Doc instance
 * @param key - Array field key (default: 'rows')
 * @returns Y.Array instance
 */
export function getYArray(ydoc: Y.Doc, key = 'rows'): Y.Array<Y.Map<any>> {
  return ydoc.getArray(key)
}

/**
 * Get Y.Map instance for general key-value storage
 *
 * @param ydoc - Y.Doc instance
 * @param key - Map field key
 * @returns Y.Map instance
 */
export function getYMap(ydoc: Y.Doc, key = 'data'): Y.Map<any> {
  return ydoc.getMap(key)
}

/**
 * Clear all cached Y.Docs and persistence providers
 * Useful for logout or cleanup
 */
export function clearAllYDocs() {
  // Destroy all persistence providers
  for (const [docId, persistence] of persistenceProviders.entries()) {
    persistence.destroy()
  }
  persistenceProviders.clear()

  // Destroy all Y.Docs
  for (const [docId, ydoc] of ydocs.entries()) {
    ydoc.destroy()
  }
  ydocs.clear()

  console.log('[YDoc] Cleared all Y.Docs')
}
