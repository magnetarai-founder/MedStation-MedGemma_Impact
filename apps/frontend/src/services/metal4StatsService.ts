/**
 * Metal4 Stats Service - Shared polling for Metal 4 performance metrics
 *
 * Prevents multiple components from polling the same endpoint simultaneously.
 * Instead, a single poller fetches data and broadcasts to all subscribers.
 *
 * Benefits:
 * - Reduces API calls by 66% (3 pollers → 1 poller)
 * - Prevents rate limit 429s from concurrent requests
 * - Centralizes backoff/retry logic
 * - Ensures consistent data across UI
 */

export interface Metal4Stats {
  queues?: Record<string, { active_buffers?: number }>
  gpu?: {
    utilization?: number
    temperature?: number
    memory_used_mb?: number
    memory_total_mb?: number
  }
  timestamp?: string
  [key: string]: any
}

type Subscriber = (stats: Metal4Stats | null) => void

class Metal4StatsService {
  private subscribers: Set<Subscriber> = new Set()
  private stats: Metal4Stats | null = null
  private polling: boolean = false
  private pollInterval: number | null = null
  private cooldownUntil: number = 0
  private failureCount: number = 0

  // Configuration
  private readonly POLL_INTERVAL_MS = 10000 // 10 seconds (reduced from 3 components × 3-10s)
  private readonly BACKOFF_MS = 60000 // 60 seconds on 429
  private readonly MAX_FAILURES = 5 // Stop polling after 5 consecutive failures

  /**
   * Subscribe to Metal4 stats updates
   *
   * @param callback - Function called with new stats (or null on error)
   * @returns Unsubscribe function
   */
  subscribe(callback: Subscriber): () => void {
    this.subscribers.add(callback)

    // Send current stats immediately
    if (this.stats) {
      callback(this.stats)
    }

    // Start polling if first subscriber
    if (this.subscribers.size === 1 && !this.polling) {
      this.startPolling()
    }

    // Return unsubscribe function
    return () => {
      this.subscribers.delete(callback)

      // Stop polling if no subscribers
      if (this.subscribers.size === 0) {
        this.stopPolling()
      }
    }
  }

  /**
   * Get current stats (synchronous)
   */
  getCurrentStats(): Metal4Stats | null {
    return this.stats
  }

  /**
   * Get current failure count
   */
  getFailureCount(): number {
    return this.failureCount
  }

  /**
   * Check if in cooldown period
   */
  isInCooldown(): boolean {
    return Date.now() < this.cooldownUntil
  }

  /**
   * Get cooldown remaining time in seconds
   */
  getCooldownRemainingSeconds(): number {
    if (!this.isInCooldown()) return 0
    return Math.ceil((this.cooldownUntil - Date.now()) / 1000)
  }

  /**
   * Force refresh (ignores cooldown)
   */
  async forceRefresh(): Promise<void> {
    await this.fetchStats()
  }

  /**
   * Start polling for Metal4 stats
   */
  private startPolling(): void {
    if (this.polling) return

    this.polling = true
    this.fetchStats() // Initial fetch

    this.pollInterval = window.setInterval(() => {
      this.fetchStats()
    }, this.POLL_INTERVAL_MS)
  }

  /**
   * Stop polling
   */
  private stopPolling(): void {
    this.polling = false

    if (this.pollInterval !== null) {
      clearInterval(this.pollInterval)
      this.pollInterval = null
    }
  }

  /**
   * Fetch Metal4 stats from backend
   */
  private async fetchStats(): Promise<void> {
    // Respect cooldown period
    if (this.isInCooldown()) {
      return
    }

    // Stop polling after too many failures
    if (this.failureCount >= this.MAX_FAILURES) {
      console.warn('[Metal4Stats] Too many failures, stopping polling')
      this.stopPolling()
      return
    }

    const token = localStorage.getItem('auth_token')
    if (!token) {
      // Not authenticated, skip polling
      return
    }

    try {
      const response = await fetch('/api/v1/monitoring/metal4', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        if (response.status === 429) {
          // Rate limited - backoff for 60 seconds
          console.warn('[Metal4Stats] Rate limited (429), backing off for 60s')
          this.cooldownUntil = Date.now() + this.BACKOFF_MS
          this.failureCount++
          this.notifySubscribers(null)
          return
        }

        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data: Metal4Stats = await response.json()
      this.stats = data
      this.failureCount = 0 // Reset on success
      this.notifySubscribers(data)

    } catch (error) {
      console.error('[Metal4Stats] Fetch failed:', error)
      this.failureCount++
      this.notifySubscribers(null)
    }
  }

  /**
   * Notify all subscribers of new stats
   */
  private notifySubscribers(stats: Metal4Stats | null): void {
    this.subscribers.forEach(callback => {
      try {
        callback(stats)
      } catch (error) {
        console.error('[Metal4Stats] Subscriber callback error:', error)
      }
    })
  }

  /**
   * Reset service state (for testing)
   */
  reset(): void {
    this.stopPolling()
    this.subscribers.clear()
    this.stats = null
    this.cooldownUntil = 0
    this.failureCount = 0
  }
}

// Singleton instance
export const metal4StatsService = new Metal4StatsService()
