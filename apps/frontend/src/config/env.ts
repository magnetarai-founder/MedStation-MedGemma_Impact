/**
 * Environment Configuration
 * Centralized access to environment variables
 */

export const env = {
  // API Configuration
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || '/api',
  apiTimeout: parseInt(import.meta.env.VITE_API_TIMEOUT || '300000'),

  // Ollama Configuration
  ollamaBaseUrl: import.meta.env.VITE_OLLAMA_BASE_URL || 'http://localhost:11434',

  // Application Settings
  appName: import.meta.env.VITE_APP_NAME || 'MagnetarStudio',
  maxFileSizeMB: parseInt(import.meta.env.VITE_MAX_FILE_SIZE_MB || '2000'),
  previewRowLimit: parseInt(import.meta.env.VITE_PREVIEW_ROW_LIMIT || '100'),

  // Feature Flags
  enableP2PChat: import.meta.env.VITE_ENABLE_P2P_CHAT === 'true',
  enableErrorTracking: import.meta.env.VITE_ENABLE_ERROR_TRACKING !== 'false', // Default true

  // Development
  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
  mode: import.meta.env.MODE,
} as const

// Validate required environment variables
if (!env.apiBaseUrl) {
  console.warn('VITE_API_BASE_URL is not set, using default: /api')
}

// Log configuration in development
if (env.isDev) {
  console.log('Environment Configuration:', {
    ...env,
    apiTimeout: `${env.apiTimeout}ms`,
    maxFileSizeMB: `${env.maxFileSizeMB}MB`,
  })
}
