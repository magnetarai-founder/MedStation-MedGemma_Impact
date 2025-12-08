/**
 * Offline Indicator Component
 * Shows online/offline status and queued operations
 */

import React, { useState, useEffect } from 'react'
import { WifiOff, Wifi, Cloud, CloudOff, Loader, AlertCircle, CheckCircle, X } from 'lucide-react'
import { offlineQueue, type OfflineOperation } from '../lib/offlineQueue'
import { serviceWorkerManager } from '../lib/serviceWorker'

export function OfflineIndicator() {
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [pendingCount, setPendingCount] = useState(0)
  const [failedCount, setFailedCount] = useState(0)
  const [showDetails, setShowDetails] = useState(false)
  const [operations, setOperations] = useState<{
    pending: OfflineOperation[]
    failed: OfflineOperation[]
    synced: OfflineOperation[]
  }>({
    pending: [],
    failed: [],
    synced: []
  })

  // Monitor online/offline status
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true)
      // Trigger sync when coming back online
      serviceWorkerManager.syncOfflineQueue()
    }

    const handleOffline = () => {
      setIsOnline(false)
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  // Monitor queue changes
  useEffect(() => {
    const updateQueue = async () => {
      try {
        const [pending, failed, synced] = await Promise.all([
          offlineQueue.getOperationsByStatus('pending'),
          offlineQueue.getOperationsByStatus('failed'),
          offlineQueue.getOperationsByStatus('synced')
        ])

        setOperations({ pending, failed, synced })
        setPendingCount(pending.length)
        setFailedCount(failed.length)
      } catch (error) {
        console.error('Failed to update queue:', error)
      }
    }

    // Initial load
    updateQueue()

    // Poll for changes every 2 seconds
    const interval = setInterval(updateQueue, 2000)

    return () => clearInterval(interval)
  }, [])

  const handleRetry = async (id: string) => {
    try {
      await offlineQueue.retryOperation(id)
      serviceWorkerManager.syncOfflineQueue()
    } catch (error) {
      console.error('Failed to retry operation:', error)
    }
  }

  const handleClearFailed = async () => {
    try {
      await offlineQueue.clearFailed()
    } catch (error) {
      console.error('Failed to clear failed operations:', error)
    }
  }

  const handleClearSynced = async () => {
    try {
      await offlineQueue.clearSynced()
    } catch (error) {
      console.error('Failed to clear synced operations:', error)
    }
  }

  // Don't show if online and no pending/failed operations
  if (isOnline && pendingCount === 0 && failedCount === 0) {
    return null
  }

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {/* Indicator Badge */}
      <div
        className={`flex items-center gap-2 px-4 py-2 rounded-lg shadow-lg cursor-pointer transition-all ${
          isOnline
            ? pendingCount > 0
              ? 'bg-blue-500 text-white'
              : 'bg-green-500 text-white'
            : 'bg-gray-800 text-white'
        }`}
        onClick={() => setShowDetails(!showDetails)}
      >
        {isOnline ? (
          pendingCount > 0 ? (
            <Loader className="w-4 h-4 animate-spin" />
          ) : (
            <Wifi className="w-4 h-4" />
          )
        ) : (
          <WifiOff className="w-4 h-4" />
        )}

        <span className="text-sm font-medium">
          {isOnline ? (
            pendingCount > 0 ? (
              `Syncing ${pendingCount} operation${pendingCount > 1 ? 's' : ''}...`
            ) : (
              'Online'
            )
          ) : (
            'Offline'
          )}
        </span>

        {failedCount > 0 && (
          <span className="flex items-center gap-1 text-sm">
            <AlertCircle className="w-4 h-4" />
            {failedCount}
          </span>
        )}
      </div>

      {/* Details Panel */}
      {showDetails && (
        <div className="absolute bottom-full right-0 mb-2 w-96 max-h-96 overflow-y-auto bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-2">
              {isOnline ? (
                <Cloud className="w-5 h-5 text-green-500" />
              ) : (
                <CloudOff className="w-5 h-5 text-gray-500" />
              )}
              <h3 className="font-semibold text-gray-900 dark:text-white">
                Offline Operations
              </h3>
            </div>
            <button
              onClick={() => setShowDetails(false)}
              className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Status Summary */}
          <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">Connection:</span>
              <span
                className={`font-medium ${
                  isOnline ? 'text-green-600' : 'text-gray-600'
                }`}
              >
                {isOnline ? 'Online' : 'Offline'}
              </span>
            </div>
            <div className="flex items-center justify-between text-sm mt-2">
              <span className="text-gray-600 dark:text-gray-400">Pending:</span>
              <span className="font-medium text-blue-600">{pendingCount}</span>
            </div>
            <div className="flex items-center justify-between text-sm mt-2">
              <span className="text-gray-600 dark:text-gray-400">Failed:</span>
              <span className="font-medium text-red-600">{failedCount}</span>
            </div>
          </div>

          {/* Pending Operations */}
          {operations.pending.length > 0 && (
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium text-gray-900 dark:text-white">
                  Pending
                </h4>
                <Loader className="w-4 h-4 text-blue-500 animate-spin" />
              </div>
              <div className="space-y-2">
                {operations.pending.map((op) => (
                  <div
                    key={op.id}
                    className="text-xs text-gray-600 dark:text-gray-400 p-2 bg-gray-50 dark:bg-gray-900 rounded"
                  >
                    <div className="font-medium">{op.method}</div>
                    <div className="truncate">{op.url}</div>
                    <div className="text-gray-500 dark:text-gray-500 mt-1">
                      {new Date(op.timestamp).toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Failed Operations */}
          {operations.failed.length > 0 && (
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium text-gray-900 dark:text-white">
                  Failed
                </h4>
                <button
                  onClick={handleClearFailed}
                  className="text-xs text-red-600 hover:text-red-700"
                >
                  Clear All
                </button>
              </div>
              <div className="space-y-2">
                {operations.failed.map((op) => (
                  <div
                    key={op.id}
                    className="text-xs text-gray-600 dark:text-gray-400 p-2 bg-red-50 dark:bg-red-900/20 rounded"
                  >
                    <div className="flex items-center justify-between">
                      <div className="font-medium">{op.method}</div>
                      <button
                        onClick={() => handleRetry(op.id)}
                        className="text-blue-600 hover:text-blue-700 text-xs"
                      >
                        Retry
                      </button>
                    </div>
                    <div className="truncate">{op.url}</div>
                    {op.error && (
                      <div className="text-red-600 dark:text-red-400 mt-1">
                        {op.error}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Synced Operations */}
          {operations.synced.length > 0 && (
            <div className="p-4">
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium text-gray-900 dark:text-white">
                  Recently Synced
                </h4>
                <button
                  onClick={handleClearSynced}
                  className="text-xs text-gray-600 hover:text-gray-700"
                >
                  Clear
                </button>
              </div>
              <div className="space-y-2">
                {operations.synced.slice(0, 5).map((op) => (
                  <div
                    key={op.id}
                    className="text-xs text-gray-600 dark:text-gray-400 p-2 bg-green-50 dark:bg-green-900/20 rounded"
                  >
                    <div className="flex items-center gap-2">
                      <CheckCircle className="w-3 h-3 text-green-600" />
                      <div className="font-medium">{op.method}</div>
                    </div>
                    <div className="truncate ml-5">{op.url}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Empty State */}
          {operations.pending.length === 0 &&
            operations.failed.length === 0 &&
            operations.synced.length === 0 && (
              <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                <CloudOff className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No offline operations</p>
              </div>
            )}
        </div>
      )}
    </div>
  )
}
