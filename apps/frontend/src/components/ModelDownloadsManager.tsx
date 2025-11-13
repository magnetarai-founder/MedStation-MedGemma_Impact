import { useEffect, useState, useRef } from 'react'
import { X, Download, CheckCircle, XCircle, RefreshCw, Loader2 } from 'lucide-react'
import { showToast } from '../lib/toast'

interface DownloadProgress {
  model_name: string
  status: 'pending' | 'downloading' | 'completed' | 'failed'
  progress?: number
  speed?: string
  size?: string
  error?: string
  timestamp?: string
}

interface ModelDownloadsManagerProps {
  onClose: () => void
  initialModel?: string // Model to start downloading immediately
}

export function ModelDownloadsManager({ onClose, initialModel }: ModelDownloadsManagerProps) {
  const [downloads, setDownloads] = useState<Record<string, DownloadProgress>>({})
  const [activeDownload, setActiveDownload] = useState<string | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    // Start downloading initial model if provided
    if (initialModel && !downloads[initialModel]) {
      startDownload(initialModel)
    }
  }, [initialModel])

  useEffect(() => {
    return () => {
      // Cleanup: close EventSource on unmount
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])

  const startDownload = async (modelName: string) => {
    // Mark as pending
    setDownloads(prev => ({
      ...prev,
      [modelName]: {
        model_name: modelName,
        status: 'pending',
        timestamp: new Date().toISOString()
      }
    }))

    setActiveDownload(modelName)

    // Close existing EventSource if any
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    // Create new EventSource for this download
    const eventSource = new EventSource(
      `/api/v1/setup/models/download/progress?model_name=${encodeURIComponent(modelName)}`
    )

    eventSourceRef.current = eventSource

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        if (data.status === 'error') {
          setDownloads(prev => ({
            ...prev,
            [modelName]: {
              model_name: modelName,
              status: 'failed',
              error: data.error || 'Download failed',
              timestamp: new Date().toISOString()
            }
          }))
          eventSource.close()
          setActiveDownload(null)
          return
        }

        if (data.status === 'completed') {
          setDownloads(prev => ({
            ...prev,
            [modelName]: {
              model_name: modelName,
              status: 'completed',
              progress: 100,
              timestamp: new Date().toISOString()
            }
          }))
          showToast.success(`Model ${modelName} downloaded successfully`)
          eventSource.close()
          setActiveDownload(null)
          return
        }

        // Update progress
        setDownloads(prev => ({
          ...prev,
          [modelName]: {
            model_name: modelName,
            status: 'downloading',
            progress: data.progress || 0,
            speed: data.speed,
            size: data.size,
            timestamp: new Date().toISOString()
          }
        }))
      } catch (error) {
        console.error('Failed to parse SSE message:', error)
      }
    }

    eventSource.onerror = (error) => {
      console.error('SSE error:', error)
      setDownloads(prev => ({
        ...prev,
        [modelName]: {
          model_name: modelName,
          status: 'failed',
          error: 'Connection lost',
          timestamp: new Date().toISOString()
        }
      }))
      eventSource.close()
      setActiveDownload(null)
    }
  }

  const retryDownload = (modelName: string) => {
    startDownload(modelName)
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <Loader2 className="w-4 h-4 animate-spin text-gray-500" />
      case 'downloading':
        return <Download className="w-4 h-4 text-blue-600 dark:text-blue-400 animate-bounce" />
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-600 dark:text-red-400" />
      default:
        return null
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'text-gray-600 dark:text-gray-400'
      case 'downloading':
        return 'text-blue-600 dark:text-blue-400'
      case 'completed':
        return 'text-green-600 dark:text-green-400'
      case 'failed':
        return 'text-red-600 dark:text-red-400'
      default:
        return 'text-gray-600 dark:text-gray-400'
    }
  }

  const downloadsList = Object.values(downloads).sort((a, b) => {
    // Active downloads first
    if (a.status === 'downloading' && b.status !== 'downloading') return -1
    if (b.status === 'downloading' && a.status !== 'downloading') return 1
    // Then by timestamp (newest first)
    return (b.timestamp || '').localeCompare(a.timestamp || '')
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
                  key={download.model_name}
                  className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-4"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      {getStatusIcon(download.status)}
                      <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                          {download.model_name}
                        </h3>
                        <p className={`text-xs ${getStatusColor(download.status)} capitalize`}>
                          {download.status}
                          {download.size && ` • ${download.size}`}
                        </p>
                      </div>
                    </div>

                    {download.status === 'failed' && (
                      <button
                        onClick={() => retryDownload(download.model_name)}
                        className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                        title="Retry download"
                      >
                        <RefreshCw size={12} />
                        Retry
                      </button>
                    )}
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
            {activeDownload ? (
              <>Downloading {activeDownload}...</>
            ) : (
              <>
                {downloadsList.filter(d => d.status === 'completed').length} completed •{' '}
                {downloadsList.filter(d => d.status === 'failed').length} failed
              </>
            )}
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
