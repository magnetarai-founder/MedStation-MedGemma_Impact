/**
 * Error Tracking Utility
 * Logs errors for monitoring and debugging
 *
 * Security: Automatically redacts sensitive data before localStorage persistence
 */

interface ErrorLog {
  timestamp: string
  type: 'error' | 'warning' | 'info'
  message: string
  stack?: string
  context?: Record<string, any>
  userAgent?: string
  url?: string
}

/**
 * Patterns to detect and redact sensitive data
 */
const SENSITIVE_PATTERNS = [
  // JWT tokens
  /eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+/g,
  // API keys (common formats)
  /\b[A-Za-z0-9]{32,}\b/g,
  // Bearer tokens
  /Bearer\s+[A-Za-z0-9-._~+/]+/gi,
  // Passwords in URLs or form data
  /password[=:]\s*[^\s&]+/gi,
  // Credit cards (basic pattern)
  /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/g,
  // SSN-like patterns
  /\b\d{3}-\d{2}-\d{4}\b/g,
  // Email addresses (optional - may be useful for debugging)
  // /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
]

/**
 * Keys that should be completely removed from logs
 */
const SENSITIVE_KEYS = [
  'password',
  'token',
  'apiKey',
  'api_key',
  'secret',
  'authorization',
  'auth',
  'bearer',
  'jwt',
  'session',
  'cookie',
  'credentials',
  'privateKey',
  'private_key',
]

/**
 * Sanitize a string by redacting sensitive patterns
 */
function sanitizeString(str: string): string {
  let sanitized = str

  for (const pattern of SENSITIVE_PATTERNS) {
    sanitized = sanitized.replace(pattern, '[REDACTED]')
  }

  return sanitized
}

/**
 * Deep sanitize an object, removing sensitive keys and redacting patterns
 */
function sanitizeObject(obj: any): any {
  if (obj === null || obj === undefined) {
    return obj
  }

  if (typeof obj === 'string') {
    return sanitizeString(obj)
  }

  if (typeof obj !== 'object') {
    return obj
  }

  if (Array.isArray(obj)) {
    return obj.map(item => sanitizeObject(item))
  }

  const sanitized: Record<string, any> = {}

  for (const [key, value] of Object.entries(obj)) {
    // Remove sensitive keys entirely
    if (SENSITIVE_KEYS.some(sensitiveKey =>
      key.toLowerCase().includes(sensitiveKey.toLowerCase())
    )) {
      sanitized[key] = '[REDACTED]'
      continue
    }

    // Recursively sanitize nested objects
    sanitized[key] = sanitizeObject(value)
  }

  return sanitized
}

/**
 * Sanitize an entire error log before persistence
 */
function sanitizeErrorLog(log: ErrorLog): ErrorLog {
  return {
    ...log,
    message: sanitizeString(log.message),
    stack: log.stack ? sanitizeString(log.stack) : undefined,
    context: log.context ? sanitizeObject(log.context) : undefined,
    url: log.url ? sanitizeUrl(log.url) : undefined,
  }
}

/**
 * Sanitize URL by removing query parameters that may contain tokens
 */
function sanitizeUrl(url: string): string {
  try {
    const urlObj = new URL(url)

    // Remove sensitive query parameters
    const sensitiveParams = ['token', 'apiKey', 'api_key', 'key', 'secret', 'auth']
    sensitiveParams.forEach(param => {
      if (urlObj.searchParams.has(param)) {
        urlObj.searchParams.set(param, '[REDACTED]')
      }
    })

    return urlObj.toString()
  } catch {
    // If URL parsing fails, just sanitize as string
    return sanitizeString(url)
  }
}

class ErrorTracker {
  private logs: ErrorLog[] = []
  private maxLogs = 100 // Keep last 100 errors in memory

  constructor() {
    // Set up global error handlers
    this.setupGlobalHandlers()
  }

  private setupGlobalHandlers() {
    // Catch unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      this.logError({
        message: `Unhandled Promise Rejection: ${event.reason}`,
        stack: event.reason?.stack,
        context: { type: 'unhandledRejection' }
      })
    })

    // Catch global errors
    window.addEventListener('error', (event) => {
      this.logError({
        message: event.message || 'Unknown error',
        stack: event.error?.stack,
        context: {
          type: 'globalError',
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno
        }
      })
    })

    // Log console errors
    const originalError = console.error
    console.error = (...args: any[]) => {
      this.logError({
        message: args.map(arg =>
          typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
        ).join(' '),
        context: { type: 'consoleError' }
      })
      originalError.apply(console, args)
    }
  }

  logError(params: {
    message: string
    stack?: string
    context?: Record<string, any>
  }) {
    const errorLog: ErrorLog = {
      timestamp: new Date().toISOString(),
      type: 'error',
      message: params.message,
      stack: params.stack,
      context: params.context,
      userAgent: navigator.userAgent,
      url: window.location.href
    }

    // Add to memory buffer
    this.logs.push(errorLog)
    if (this.logs.length > this.maxLogs) {
      this.logs.shift() // Remove oldest
    }

    // Store in localStorage for persistence
    this.persistToStorage(errorLog)

    // In production, you could send to a backend endpoint here
    // await fetch('/api/errors', { method: 'POST', body: JSON.stringify(errorLog) })
  }

  logWarning(message: string, context?: Record<string, any>) {
    const log: ErrorLog = {
      timestamp: new Date().toISOString(),
      type: 'warning',
      message,
      context,
      url: window.location.href
    }
    this.logs.push(log)
    this.persistToStorage(log)
  }

  logInfo(message: string, context?: Record<string, any>) {
    const log: ErrorLog = {
      timestamp: new Date().toISOString(),
      type: 'info',
      message,
      context,
      url: window.location.href
    }
    this.logs.push(log)
    this.persistToStorage(log)
  }

  private persistToStorage(log: ErrorLog) {
    try {
      // SECURITY: Sanitize log before localStorage to prevent secret leakage
      const sanitizedLog = sanitizeErrorLog(log)

      const stored = localStorage.getItem('error_logs')
      const logs: ErrorLog[] = stored ? JSON.parse(stored) : []
      logs.push(sanitizedLog)

      // Keep only last 50 in localStorage to avoid quota issues
      if (logs.length > 50) {
        logs.splice(0, logs.length - 50)
      }

      localStorage.setItem('error_logs', JSON.stringify(logs))
    } catch (error) {
      // Silently fail if localStorage is unavailable
      console.warn('Failed to persist error log:', error)
    }
  }

  getLogs(type?: 'error' | 'warning' | 'info'): ErrorLog[] {
    if (type) {
      return this.logs.filter(log => log.type === type)
    }
    return [...this.logs]
  }

  getStoredLogs(): ErrorLog[] {
    try {
      const stored = localStorage.getItem('error_logs')
      return stored ? JSON.parse(stored) : []
    } catch {
      return []
    }
  }

  clearLogs() {
    this.logs = []
    try {
      localStorage.removeItem('error_logs')
    } catch {
      // Silently fail
    }
  }

  exportLogs(): string {
    const allLogs = this.getStoredLogs()
    return JSON.stringify(allLogs, null, 2)
  }

  downloadLogs() {
    const logs = this.exportLogs()
    const blob = new Blob([logs], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `error-logs-${new Date().toISOString().slice(0, 10)}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }
}

// Create singleton instance
export const errorTracker = new ErrorTracker()

// Export a convenience function for manual error tracking
export function trackError(message: string, context?: Record<string, any>) {
  errorTracker.logError({ message, context })
}

export function trackWarning(message: string, context?: Record<string, any>) {
  errorTracker.logWarning(message, context)
}

export function trackInfo(message: string, context?: Record<string, any>) {
  errorTracker.logInfo(message, context)
}
