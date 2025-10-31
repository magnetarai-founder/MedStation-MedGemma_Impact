/**
 * Service Worker Registration and Management
 * Handles offline support and PWA capabilities
 */

export interface ServiceWorkerConfig {
  onSuccess?: (registration: ServiceWorkerRegistration) => void
  onUpdate?: (registration: ServiceWorkerRegistration) => void
  onOffline?: () => void
  onOnline?: () => void
  onSyncComplete?: (operation: any) => void
  onSyncFailed?: (operation: any, error: string) => void
}

class ServiceWorkerManager {
  private registration: ServiceWorkerRegistration | null = null
  private config: ServiceWorkerConfig = {}
  private isOnline = navigator.onLine

  /**
   * Register the service worker
   */
  async register(config: ServiceWorkerConfig = {}): Promise<void> {
    this.config = config

    if (!('serviceWorker' in navigator)) {
      console.warn('Service Worker not supported in this browser')
      return
    }

    try {
      // Register service worker
      this.registration = await navigator.serviceWorker.register('/sw.js', {
        scope: '/'
      })

      console.log('Service Worker registered:', this.registration.scope)

      // Handle updates
      this.registration.addEventListener('updatefound', () => {
        const newWorker = this.registration!.installing
        if (newWorker) {
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              // New service worker available
              console.log('New service worker available')
              config.onUpdate?.(this.registration!)
            }
          })
        }
      })

      // Listen for messages from service worker
      navigator.serviceWorker.addEventListener('message', (event) => {
        this.handleServiceWorkerMessage(event.data)
      })

      // Monitor online/offline status
      window.addEventListener('online', this.handleOnline)
      window.addEventListener('offline', this.handleOffline)

      // Initial status
      if (this.isOnline) {
        this.syncOfflineQueue()
      }

      config.onSuccess?.(this.registration)
    } catch (error) {
      console.error('Service Worker registration failed:', error)
    }
  }

  /**
   * Unregister the service worker
   */
  async unregister(): Promise<boolean> {
    if (this.registration) {
      const success = await this.registration.unregister()
      if (success) {
        console.log('Service Worker unregistered')
        this.registration = null
      }
      return success
    }
    return false
  }

  /**
   * Update the service worker
   */
  async update(): Promise<void> {
    if (this.registration) {
      await this.registration.update()
      console.log('Service Worker update checked')
    }
  }

  /**
   * Skip waiting and activate new service worker immediately
   */
  skipWaiting(): void {
    if (this.registration?.waiting) {
      this.registration.waiting.postMessage({ type: 'SKIP_WAITING' })
    }
  }

  /**
   * Cache a file manually
   */
  cacheFile(url: string, data: any): void {
    this.postMessage({
      type: 'CACHE_FILE',
      payload: { url, data }
    })
  }

  /**
   * Clear all caches
   */
  clearCache(): void {
    this.postMessage({ type: 'CLEAR_CACHE' })
  }

  /**
   * Get cache size
   */
  async getCacheSize(): Promise<number> {
    return new Promise((resolve) => {
      if (!this.registration?.active) {
        resolve(0)
        return
      }

      const messageChannel = new MessageChannel()
      messageChannel.port1.onmessage = (event) => {
        resolve(event.data.size || 0)
      }

      this.registration.active.postMessage(
        { type: 'GET_CACHE_SIZE' },
        [messageChannel.port2]
      )
    })
  }

  /**
   * Sync offline queue
   */
  syncOfflineQueue(): void {
    this.postMessage({ type: 'SYNC_QUEUE' })
  }

  /**
   * Check if app is online
   */
  isAppOnline(): boolean {
    return this.isOnline
  }

  /**
   * Post message to service worker
   */
  private postMessage(message: any): void {
    if (this.registration?.active) {
      this.registration.active.postMessage(message)
    }
  }

  /**
   * Handle messages from service worker
   */
  private handleServiceWorkerMessage(data: any): void {
    const { type, operation, error } = data

    switch (type) {
      case 'SYNC_SUCCESS':
        console.log('Offline operation synced:', operation)
        this.config.onSyncComplete?.(operation)
        break

      case 'SYNC_FAILED':
        console.error('Offline operation sync failed:', operation, error)
        this.config.onSyncFailed?.(operation, error)
        break
    }
  }

  /**
   * Handle online event
   */
  private handleOnline = (): void => {
    console.log('App is now online')
    this.isOnline = true
    this.config.onOnline?.()

    // Sync queued operations
    this.syncOfflineQueue()
  }

  /**
   * Handle offline event
   */
  private handleOffline = (): void => {
    console.log('App is now offline')
    this.isOnline = false
    this.config.onOffline?.()
  }
}

// Export singleton instance
export const serviceWorkerManager = new ServiceWorkerManager()

/**
 * Register service worker with configuration
 */
export async function registerServiceWorker(config: ServiceWorkerConfig = {}): Promise<void> {
  await serviceWorkerManager.register(config)
}

/**
 * Unregister service worker
 */
export async function unregisterServiceWorker(): Promise<boolean> {
  return serviceWorkerManager.unregister()
}
