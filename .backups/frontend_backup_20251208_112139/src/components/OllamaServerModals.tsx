import { useState, useEffect } from 'react'
import { X, AlertTriangle, Power, RotateCcw, Loader2 } from 'lucide-react'

interface ShutdownModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => Promise<void>
  loadedModels: string[]
}

export function ShutdownModal({ isOpen, onClose, onConfirm, loadedModels }: ShutdownModalProps) {
  const [isShuttingDown, setIsShuttingDown] = useState(false)

  // Handle Escape key to close modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [onClose])

  const handleConfirm = async () => {
    setIsShuttingDown(true)
    try {
      await onConfirm()
    } finally {
      setIsShuttingDown(false)
      onClose()
    }
  }

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center">
        {/* Modal */}
        <div className="relative bg-white dark:bg-gray-900 rounded-2xl shadow-2xl max-w-md w-full mx-4 border border-red-200 dark:border-red-800">
          {/* Header */}
          <div className="flex items-center gap-3 px-6 py-4 border-b border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20">
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/40 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" />
            </div>
            <div className="flex-1">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Shutdown Ollama Server?
              </h2>
              <p className="text-sm text-red-600 dark:text-red-400 mt-0.5">
                This will unload all models and stop the server
              </p>
            </div>
            <button
              onClick={onClose}
              disabled={isShuttingDown}
              className="flex-shrink-0 p-2 hover:bg-red-100 dark:hover:bg-red-900/40 rounded-lg transition-colors disabled:opacity-50"
            >
              <X size={20} className="text-gray-500" />
            </button>
          </div>

          {/* Content */}
          <div className="px-6 py-4">
            <div className="space-y-4">
              <p className="text-sm text-gray-700 dark:text-gray-300">
                The following {loadedModels.length} model{loadedModels.length !== 1 ? 's' : ''} will be unloaded from memory:
              </p>

              {loadedModels.length > 0 ? (
                <div className="max-h-32 overflow-y-auto bg-gray-50 dark:bg-gray-800 rounded-lg p-3 space-y-1.5">
                  {loadedModels.map((model, index) => (
                    <div
                      key={index}
                      className="flex items-center gap-2 text-sm text-gray-900 dark:text-gray-100"
                    >
                      <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
                      <span>{model}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400 italic">
                  No models currently loaded
                </p>
              )}

              <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
                <p className="text-xs text-amber-800 dark:text-amber-200">
                  ⚠️ <strong>Warning:</strong> All active chat sessions will be interrupted. You can restart the server by clicking the logo again.
                </p>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={onClose}
              disabled={isShuttingDown}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirm}
              disabled={isShuttingDown}
              className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
            >
              {isShuttingDown ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Shutting Down...
                </>
              ) : (
                <>
                  <Power className="w-4 h-4" />
                  Shutdown Server
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}

interface RestartModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: (reloadModels: boolean, modelsToLoad: string[]) => Promise<void>
  previousModels: string[]
}

export function RestartModal({ isOpen, onClose, onConfirm, previousModels }: RestartModalProps) {
  const [isRestarting, setIsRestarting] = useState(false)
  const [reloadModels, setReloadModels] = useState(true)
  const [selectedModels, setSelectedModels] = useState<Set<string>>(new Set(previousModels))

  // Handle Escape key to close modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [onClose])

  const handleConfirm = async () => {
    setIsRestarting(true)
    try {
      const modelsToLoad = reloadModels ? Array.from(selectedModels) : []
      await onConfirm(reloadModels, modelsToLoad)
    } finally {
      setIsRestarting(false)
      onClose()
    }
  }

  const toggleModel = (model: string) => {
    const newSelected = new Set(selectedModels)
    if (newSelected.has(model)) {
      newSelected.delete(model)
    } else {
      newSelected.add(model)
    }
    setSelectedModels(newSelected)
  }

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center">
        {/* Modal */}
        <div className="relative bg-white dark:bg-gray-900 rounded-2xl shadow-2xl max-w-md w-full mx-4 border border-primary-200 dark:border-primary-800">
          {/* Header */}
          <div className="flex items-center gap-3 px-6 py-4 border-b border-primary-200 dark:border-primary-800 bg-primary-50 dark:bg-primary-900/20">
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-primary-100 dark:bg-primary-900/40 flex items-center justify-center">
              <RotateCcw className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            </div>
            <div className="flex-1">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Start Ollama Server
              </h2>
              <p className="text-sm text-primary-600 dark:text-primary-400 mt-0.5">
                Restart and optionally reload models
              </p>
            </div>
            <button
              onClick={onClose}
              disabled={isRestarting}
              className="flex-shrink-0 p-2 hover:bg-primary-100 dark:hover:bg-primary-900/40 rounded-lg transition-colors disabled:opacity-50"
            >
              <X size={20} className="text-gray-500" />
            </button>
          </div>

          {/* Content */}
          <div className="px-6 py-4">
            <div className="space-y-4">
              {previousModels.length > 0 ? (
                <>
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Reload Previous Models
                    </label>
                    <button
                      onClick={() => setReloadModels(!reloadModels)}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        reloadModels ? 'bg-primary-600' : 'bg-gray-300 dark:bg-gray-600'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          reloadModels ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </div>

                  {reloadModels && (
                    <div className="space-y-2">
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Select models to reload ({selectedModels.size} selected):
                      </p>
                      <div className="max-h-40 overflow-y-auto bg-gray-50 dark:bg-gray-800 rounded-lg p-3 space-y-2">
                        {previousModels.map((model, index) => (
                          <label
                            key={index}
                            className="flex items-center gap-3 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 p-2 rounded-lg transition-colors"
                          >
                            <input
                              type="checkbox"
                              checked={selectedModels.has(model)}
                              onChange={() => toggleModel(model)}
                              className="w-4 h-4 text-primary-600 rounded border-gray-300 dark:border-gray-600"
                            />
                            <span className="text-sm text-gray-900 dark:text-gray-100 flex-1">
                              {model}
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                  <p className="text-sm text-blue-800 dark:text-blue-200">
                    No models were previously loaded. Server will start with a clean state.
                  </p>
                </div>
              )}

              <div className="p-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
                <p className="text-xs text-gray-600 dark:text-gray-400">
                  ℹ️ Server will start in the background. Models can be loaded later via Model Management.
                </p>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={onClose}
              disabled={isRestarting}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirm}
              disabled={isRestarting}
              className="px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
            >
              {isRestarting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Starting...
                </>
              ) : (
                <>
                  <Power className="w-4 h-4" />
                  Start Server
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
