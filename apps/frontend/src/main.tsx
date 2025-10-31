import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import { ErrorBoundary } from './components/ErrorBoundary'
import { errorTracker } from './lib/errorTracking'
import { registerServiceWorker } from './lib/serviceWorker'
import './index.css'

// Initialize error tracking
errorTracker.logInfo('Application started')

// Register service worker for offline support
if (process.env.NODE_ENV === 'production') {
  registerServiceWorker({
    onSuccess: () => {
      console.log('Service worker registered successfully')
      errorTracker.logInfo('Service worker registered')
    },
    onUpdate: () => {
      console.log('New service worker available')
      errorTracker.logInfo('Service worker update available')
    },
    onOffline: () => {
      console.log('App is offline')
      errorTracker.logInfo('App went offline')
    },
    onOnline: () => {
      console.log('App is online')
      errorTracker.logInfo('App came online')
    },
    onSyncComplete: (operation) => {
      console.log('Offline operation synced:', operation)
      errorTracker.logInfo('Offline operation synced', { operation })
    },
    onSyncFailed: (operation, error) => {
      console.error('Offline operation sync failed:', operation, error)
      errorTracker.logError(new Error(`Sync failed: ${error}`), { operation })
    }
  })
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
    mutations: {
      // Don't cancel mutations when components unmount (e.g., downloads)
      gcTime: Infinity,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <ErrorBoundary>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </ErrorBoundary>,
)
