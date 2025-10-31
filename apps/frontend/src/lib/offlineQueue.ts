/**
 * Offline Queue Management
 * Provides utilities for working with offline operations queue
 */

const DB_NAME = 'ElohimOSVault'
const DB_VERSION = 1
const QUEUE_STORE = 'offlineQueue'

export interface OfflineOperation {
  id: string
  url: string
  method: string
  headers: Record<string, string>
  body: string
  timestamp: number
  status: 'pending' | 'synced' | 'failed'
  syncedAt?: number
  error?: string
}

class OfflineQueueManager {
  private db: IDBDatabase | null = null

  /**
   * Initialize IndexedDB connection
   */
  async init(): Promise<void> {
    if (this.db) return

    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION)

      request.onerror = () => {
        console.error('Failed to open IndexedDB:', request.error)
        reject(request.error)
      }

      request.onsuccess = () => {
        this.db = request.result
        console.log('IndexedDB connected')
        resolve()
      }

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result

        // Create offline queue store
        if (!db.objectStoreNames.contains(QUEUE_STORE)) {
          const queueStore = db.createObjectStore(QUEUE_STORE, { keyPath: 'id' })
          queueStore.createIndex('status', 'status', { unique: false })
          queueStore.createIndex('timestamp', 'timestamp', { unique: false })
          console.log('Created offline queue store')
        }
      }
    })
  }

  /**
   * Get all operations
   */
  async getAllOperations(): Promise<OfflineOperation[]> {
    await this.init()
    if (!this.db) return []

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(QUEUE_STORE, 'readonly')
      const store = transaction.objectStore(QUEUE_STORE)
      const request = store.getAll()

      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })
  }

  /**
   * Get operations by status
   */
  async getOperationsByStatus(status: 'pending' | 'synced' | 'failed'): Promise<OfflineOperation[]> {
    await this.init()
    if (!this.db) return []

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(QUEUE_STORE, 'readonly')
      const store = transaction.objectStore(QUEUE_STORE)
      const index = store.index('status')
      const request = index.getAll(status)

      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })
  }

  /**
   * Get pending operations count
   */
  async getPendingCount(): Promise<number> {
    const pending = await this.getOperationsByStatus('pending')
    return pending.length
  }

  /**
   * Get failed operations count
   */
  async getFailedCount(): Promise<number> {
    const failed = await this.getOperationsByStatus('failed')
    return failed.length
  }

  /**
   * Delete an operation
   */
  async deleteOperation(id: string): Promise<void> {
    await this.init()
    if (!this.db) return

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(QUEUE_STORE, 'readwrite')
      const store = transaction.objectStore(QUEUE_STORE)
      const request = store.delete(id)

      request.onsuccess = () => resolve()
      request.onerror = () => reject(request.error)
    })
  }

  /**
   * Clear all synced operations
   */
  async clearSynced(): Promise<void> {
    const synced = await this.getOperationsByStatus('synced')
    for (const operation of synced) {
      await this.deleteOperation(operation.id)
    }
  }

  /**
   * Clear all failed operations
   */
  async clearFailed(): Promise<void> {
    const failed = await this.getOperationsByStatus('failed')
    for (const operation of failed) {
      await this.deleteOperation(operation.id)
    }
  }

  /**
   * Clear all operations
   */
  async clearAll(): Promise<void> {
    await this.init()
    if (!this.db) return

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(QUEUE_STORE, 'readwrite')
      const store = transaction.objectStore(QUEUE_STORE)
      const request = store.clear()

      request.onsuccess = () => {
        console.log('Offline queue cleared')
        resolve()
      }
      request.onerror = () => reject(request.error)
    })
  }

  /**
   * Retry a failed operation
   */
  async retryOperation(id: string): Promise<void> {
    await this.init()
    if (!this.db) return

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(QUEUE_STORE, 'readwrite')
      const store = transaction.objectStore(QUEUE_STORE)
      const getRequest = store.get(id)

      getRequest.onsuccess = () => {
        const operation = getRequest.result
        if (operation) {
          operation.status = 'pending'
          delete operation.error
          delete operation.syncedAt

          const putRequest = store.put(operation)
          putRequest.onsuccess = () => resolve()
          putRequest.onerror = () => reject(putRequest.error)
        } else {
          reject(new Error('Operation not found'))
        }
      }
      getRequest.onerror = () => reject(getRequest.error)
    })
  }

  /**
   * Get operation details
   */
  async getOperation(id: string): Promise<OfflineOperation | null> {
    await this.init()
    if (!this.db) return null

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction(QUEUE_STORE, 'readonly')
      const store = transaction.objectStore(QUEUE_STORE)
      const request = store.get(id)

      request.onsuccess = () => resolve(request.result || null)
      request.onerror = () => reject(request.error)
    })
  }

  /**
   * Subscribe to queue changes
   */
  onChange(callback: () => void): () => void {
    // Set up periodic polling (since IndexedDB doesn't have native change events)
    const interval = setInterval(callback, 1000)

    // Return unsubscribe function
    return () => clearInterval(interval)
  }
}

// Export singleton instance
export const offlineQueue = new OfflineQueueManager()

/**
 * Hook-friendly functions for React components
 */
export async function useOfflineQueueData() {
  const [pending, failed, synced] = await Promise.all([
    offlineQueue.getOperationsByStatus('pending'),
    offlineQueue.getOperationsByStatus('failed'),
    offlineQueue.getOperationsByStatus('synced')
  ])

  return {
    pending,
    failed,
    synced,
    pendingCount: pending.length,
    failedCount: failed.length,
    syncedCount: synced.length
  }
}
