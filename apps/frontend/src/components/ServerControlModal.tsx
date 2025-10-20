import { useState } from 'react'
import { X, Power, RefreshCw } from 'lucide-react'
import { useOllamaStore } from '../stores/ollamaStore'

interface ServerControlModalProps {
  isOpen: boolean
  onClose: () => void
}

export function ServerControlModal({ isOpen, onClose }: ServerControlModalProps) {
  const { serverStatus, fetchServerStatus } = useOllamaStore()
  const [isShuttingDown, setIsShuttingDown] = useState(false)
  const [isRestarting, setIsRestarting] = useState(false)

  if (!isOpen) return null

  const handleShutdown = async () => {
    setIsShuttingDown(true)
    try {
      const response = await fetch(`/api/v1/chat/ollama/server/shutdown`, {
        method: 'POST'
      })

      if (response.ok) {
        await fetchServerStatus()
        onClose()
      } else {
        alert('Failed to shutdown Ollama server')
      }
    } catch (error) {
      console.error('Failed to shutdown Ollama:', error)
      alert('Failed to shutdown Ollama server')
    } finally {
      setIsShuttingDown(false)
    }
  }

  const handleRestart = async () => {
    setIsRestarting(true)
    try {
      const response = await fetch(
        `/api/v1/chat/ollama/server/restart?reload_models=true`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ models_to_load: serverStatus.loadedModels })
        }
      )

      if (response.ok) {
        // Wait for startup
        setTimeout(async () => {
          await fetchServerStatus()
          onClose()
        }, 3000)
      } else {
        alert('Failed to restart Ollama server')
        setIsRestarting(false)
      }
    } catch (error) {
      console.error('Failed to restart Ollama:', error)
      alert('Failed to restart Ollama server')
      setIsRestarting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="w-full max-w-md bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Power className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Ollama Server Controls
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
          >
            <X className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Server Status */}
          <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Status</span>
              <span className={`text-sm font-semibold ${serverStatus.running ? 'text-green-600' : 'text-red-600'}`}>
                {serverStatus.running ? 'Running' : 'Stopped'}
              </span>
            </div>
            {serverStatus.running && (
              <div className="text-xs text-gray-600 dark:text-gray-400">
                {serverStatus.modelCount} model{serverStatus.modelCount !== 1 ? 's' : ''} loaded
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="space-y-3">
            {serverStatus.running ? (
              <>
                <button
                  onClick={handleRestart}
                  disabled={isRestarting}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-400 text-white rounded-lg font-medium transition-colors"
                >
                  <RefreshCw className={`w-4 h-4 ${isRestarting ? 'animate-spin' : ''}`} />
                  {isRestarting ? 'Restarting...' : 'Restart Server'}
                </button>
                <button
                  onClick={handleShutdown}
                  disabled={isShuttingDown}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-red-500 hover:bg-red-600 disabled:bg-red-400 text-white rounded-lg font-medium transition-colors"
                >
                  <Power className="w-4 h-4" />
                  {isShuttingDown ? 'Shutting down...' : 'Shutdown Server'}
                </button>
              </>
            ) : (
              <button
                onClick={handleRestart}
                disabled={isRestarting}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-green-500 hover:bg-green-600 disabled:bg-green-400 text-white rounded-lg font-medium transition-colors"
              >
                <Power className="w-4 h-4" />
                {isRestarting ? 'Starting...' : 'Start Server'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
