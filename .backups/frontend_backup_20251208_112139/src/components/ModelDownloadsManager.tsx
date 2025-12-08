import { useEffect, useState, useRef } from 'react'
import { X, Download, CheckCircle, XCircle, RefreshCw, Loader2, Ban } from 'lucide-react'
import { showToast } from '../lib/toast'
import { authFetch } from '../lib/api'

interface DownloadProgress {
  name: string
  status: 'queued' | 'downloading' | 'completed' | 'failed' | 'canceled'
  progress?: number
  speed?: string | null
  error?: string | null
  position?: number | null
  started_at?: string | null
  completed_at?: string | null
}

interface ModelDownloadsManagerProps {
  onClose: () => void
  initialModel?: string // Model to start downloading immediately
}

export function ModelDownloadsManager({ onClose, initialModel }: ModelDownloadsManagerProps) {
  const [downloads, setDownloads] = useState<DownloadProgress[]>([])
  const [loading, setLoading] = useState(true)
  const pollIntervalRef = useRef<number | null>(null)
  const notifiedRef = useRef<Set<string>>(new Set()) // Track which downloads we've notified about

  useEffect(() => {
    // Start downloading initial model if provided
    if (initialModel) {
      enqueueDownload(initialModel)
    }

    // Start polling for status
    fetchStatus()
    startPolling()

    return () => {
      stopPolling()
    }
  }, [])

  const startPolling = () => {
    // Poll every 2 seconds for status updates
    pollIntervalRef.current = window.setInterval(() => {
      fetchStatus()
    }, 2000)
  }

  const stopPolling = () => {
    if (pollIntervalRef.current !== null) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
  }

  const fetchStatus = async () => {
    try {
      const response = await authFetch('/api/v1/models/downloads/status')
      if (response.ok) {
        const data = await response.json()
        const newDownloads = data.downloads || []

        // Check for completed downloads and send notifications
        newDownloads.forEach((download: DownloadProgress) => {
          if (download.status === 'completed' && !notifiedRef.current.has(download.name)) {
            notifiedRef.current.add(download.name)
            showDesktopNotification(download.name)
            showToast.success(`${download.name} downloaded successfully`)
          }
        })

        setDownloads(newDownloads)
        setLoading(false)
      }
    } catch (error) {
      console.error('Failed to fetch download status:', error)
      setLoading(false)
    }
  }

  const enqueueDownload = async (modelName: string) => {
    try {
      const response = await authFetch('/api/v1/models/downloads/enqueue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ models: [modelName] })
      })

      if (response.ok) {
        const data = await response.json()
        if (data.enqueued.length > 0) {
          showToast.success(`${modelName} added to download queue`)
          fetchStatus() // Refresh immediately
        } else {
          showToast.info(`${modelName} is already queued or downloading`)
        }
      }
    } catch (error) {
      console.error('Failed to enqueue download:', error)
      showToast.error('Failed to start download')
    }
  }

  const cancelDownload = async (modelName: string) => {
    try {
      const response = await authFetch(`/api/v1/models/downloads/${encodeURIComponent(modelName)}/cancel`, {
        method: 'POST'
      })

      if (response.ok) {
        showToast.success(`${modelName} download canceled`)
        fetchStatus() // Refresh immediately
      }
    } catch (error) {
      console.error('Failed to cancel download:', error)
      showToast.error('Failed to cancel download')
    }
  }

  const retryDownload = (modelName: string) => {
    enqueueDownload(modelName)
  }

  const showDesktopNotification = (modelName: string) => {
    // Check if notifications are supported and permitted
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('Model Download Complete', {
        body: `${modelName} is ready to use`,
        icon: '/favicon.ico'
      })
    } else if ('Notification' in window && Notification.permission !== 'denied') {
      // Request permission
      Notification.requestPermission().then(permission => {
        if (permission === 'granted') {
          new Notification('Model Download Complete', {
            body: `${modelName} is ready to use`,
            icon: '/favicon.ico'
          })
        }
      })
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'queued':
        return <Loader2 className="w-4 h-4 animate-spin text-gray-500" />
      case 'downloading':
        return <Download className="w-4 h-4 text-blue-600 dark:text-blue-400 animate-bounce" />
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-600 dark:text-red-400" />
      case 'canceled':
        return <Ban className="w-4 h-4 text-orange-600 dark:text-orange-400" />
      default:
        return null
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'queued':
        return 'text-gray-600 dark:text-gray-400'
      case 'downloading':
        return 'text-blue-600 dark:text-blue-400'
      case 'completed':
        return 'text-green-600 dark:text-green-400'
      case 'failed':
        return 'text-red-600 dark:text-red-400'
      case 'canceled':
        return 'text-orange-600 dark:text-orange-400'
      default:
        return 'text-gray-600 dark:text-gray-400'
    }
  }

  const downloadsList = downloads.sort((a, b) => {
    // Active downloads first
    if (a.status === 'downloading' && b.status !== 'downloading') return -1
    if (b.status === 'downloading' && a.status !== 'downloading') return 1
    // Queued second
    if (a.status === 'queued' && b.status !== 'queued') return -1
    if (b.status === 'queued' && a.status !== 'queued') return 1
    // Then by timestamp (newest first)
    return (b.started_at || b.completed_at || '').localeCompare(a.started_at || a.completed_at || '')
  })

  return (
    <div className="fixed inset-0 bg-black/50 dark:bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-3xl w-full max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              Model Downloads
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Track and manage model download progress
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {downloadsList.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Download size={48} className="text-gray-400 mb-4" />
              <p className="text-gray-600 dark:text-gray-400 text-center">
                No downloads yet
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-500 mt-2 text-center">
                Start a download from the Model Management sidebar
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {downloadsList.map((download) => (
                <div
                  key={download.name}
                  className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-4"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      {getStatusIcon(download.status)}
                      <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                          {download.name}
                        </h3>
                        <p className={`text-xs ${getStatusColor(download.status)} capitalize`}>
                          {download.status}
                          {download.position && ` • Position: ${download.position}`}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {/* Cancel button for queued/downloading */}
                      {(download.status === 'queued' || download.status === 'downloading') && (
                        <button
                          onClick={() => cancelDownload(download.name)}
                          className="flex items-center gap-1 px-2 py-1 text-xs bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
                          title="Cancel download"
                        >
                          <X size={12} />
                          Cancel
                        </button>
                      )}

                      {/* Retry button for failed/canceled */}
                      {(download.status === 'failed' || download.status === 'canceled') && (
                        <button
                          onClick={() => retryDownload(download.name)}
                          className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                          title="Retry download"
                        >
                          <RefreshCw size={12} />
                          Retry
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Progress Bar */}
                  {download.status === 'downloading' && download.progress !== undefined && (
                    <div className="mt-2">
                      <div className="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400 mb-1">
                        <span>{Math.round(download.progress)}%</span>
                        {download.speed && <span>{download.speed}</span>}
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                        <div
                          className="bg-blue-600 h-full transition-all duration-300 ease-out"
                          style={{ width: `${download.progress}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Error Message */}
                  {download.status === 'failed' && download.error && (
                    <p className="mt-2 text-xs text-red-600 dark:text-red-400">
                      {download.error}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-between items-center">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {downloadsList.filter(d => d.status === 'downloading').length} active •{' '}
            {downloadsList.filter(d => d.status === 'queued').length} queued •{' '}
            {downloadsList.filter(d => d.status === 'completed').length} completed
          </p>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
