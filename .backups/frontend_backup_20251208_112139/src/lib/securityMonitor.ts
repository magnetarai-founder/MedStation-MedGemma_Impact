/**
 * Security Monitor for ElohimOS
 *
 * Handles auto-lock, screenshot blocking, and other security features.
 */

import { useDocsStore } from '@/stores/docsStore'

/**
 * Inactivity timer for auto-lock
 */
let inactivityTimer: NodeJS.Timeout | null = null
let lastActivityTime = Date.now()

/**
 * Converts inactivity setting to milliseconds
 */
function getInactivityTimeout(setting: string): number {
  switch (setting) {
    case 'instant':
      return 0
    case '30s':
      return 30 * 1000
    case '1m':
      return 60 * 1000
    case '2m':
      return 2 * 60 * 1000
    case '3m':
      return 3 * 60 * 1000
    case '4m':
      return 4 * 60 * 1000
    case '5m':
      return 5 * 60 * 1000
    default:
      return 5 * 60 * 1000
  }
}

/**
 * Resets the inactivity timer
 */
export function resetInactivityTimer() {
  lastActivityTime = Date.now()
  useDocsStore.getState().updateActivity()

  const { securitySettings, vaultUnlocked, lockVault } = useDocsStore.getState()

  // Only start timer if vault is unlocked
  if (!vaultUnlocked) {
    return
  }

  // Clear existing timer
  if (inactivityTimer) {
    clearTimeout(inactivityTimer)
  }

  // Set new timer
  const timeout = getInactivityTimeout(securitySettings.inactivity_lock)

  if (timeout === 0) {
    // Instant lock - don't set a timer
    return
  }

  inactivityTimer = setTimeout(() => {
    // Double-check if still unlocked before locking
    const state = useDocsStore.getState()
    if (state.vaultUnlocked) {
      console.log('Auto-locking vault due to inactivity')
      lockVault()
      // Also lock all insights
      state.lockAllInsights()
    }
  }, timeout)
}

/**
 * Stops the inactivity timer
 */
export function stopInactivityTimer() {
  if (inactivityTimer) {
    clearTimeout(inactivityTimer)
    inactivityTimer = null
  }
}

/**
 * Sets up activity listeners for auto-lock
 */
export function setupActivityListeners() {
  // Track user activity
  const activityEvents = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart']

  activityEvents.forEach(event => {
    document.addEventListener(event, resetInactivityTimer, { passive: true })
  })

  // Handle page visibility changes
  document.addEventListener('visibilitychange', () => {
    const { securitySettings, vaultUnlocked, lockVault, lockAllInsights } = useDocsStore.getState()

    if (document.hidden) {
      // Page is hidden (user switched tabs or minimized)
      if (securitySettings.lock_on_exit && vaultUnlocked) {
        console.log('Auto-locking vault due to page visibility change')
        lockVault()
        lockAllInsights()
      }
    } else {
      // Page is visible again
      resetInactivityTimer()
    }
  })

  // Handle window blur/focus
  window.addEventListener('blur', () => {
    const { securitySettings, vaultUnlocked, lockVault, lockAllInsights } = useDocsStore.getState()

    if (securitySettings.lock_on_exit && vaultUnlocked) {
      console.log('Auto-locking vault due to window blur')
      lockVault()
      lockAllInsights()
    }
  })

  window.addEventListener('focus', () => {
    resetInactivityTimer()
  })

  // Start the initial timer
  resetInactivityTimer()
}

/**
 * Removes activity listeners
 */
export function removeActivityListeners() {
  const activityEvents = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart']

  activityEvents.forEach(event => {
    document.removeEventListener(event, resetInactivityTimer)
  })

  stopInactivityTimer()
}

/**
 * Attempts to block screenshots using CSS (limited browser support)
 */
export function setupScreenshotProtection() {
  const { securitySettings } = useDocsStore.getState()

  if (securitySettings.disable_screenshots) {
    // Apply CSS that hints to browsers to block screenshots
    document.documentElement.style.setProperty('-webkit-user-select', 'none')
    document.documentElement.style.setProperty('user-select', 'none')

    // Note: True screenshot blocking requires native apps or browser extensions
    // This is a best-effort approach for web apps
    console.log('Screenshot protection enabled (limited browser support)')
  } else {
    document.documentElement.style.removeProperty('-webkit-user-select')
    document.documentElement.style.removeProperty('user-select')
  }
}

/**
 * Initialize security monitor
 */
export function initializeSecurityMonitor() {
  console.log('Initializing security monitor...')
  setupActivityListeners()
  setupScreenshotProtection()

  // Re-apply screenshot protection when settings change
  // This is handled by the settings component
}

/**
 * Cleanup security monitor
 */
export function cleanupSecurityMonitor() {
  console.log('Cleaning up security monitor...')
  removeActivityListeners()
  document.documentElement.style.removeProperty('-webkit-user-select')
  document.documentElement.style.removeProperty('user-select')
}
