import { useState, useEffect } from 'react'
import { Cpu } from 'lucide-react'
import { QuickChatDropdown } from './QuickChatDropdown'
import { ModelManagementSidebar } from './ModelManagementSidebar'
import { useOllamaStore } from '../stores/ollamaStore'
import { ShutdownModal, RestartModal } from './OllamaServerModals'

export function Header() {
  const [showModelSidebar, setShowModelSidebar] = useState(false)
  const { serverStatus, fetchServerStatus } = useOllamaStore()
  const [showShutdownModal, setShowShutdownModal] = useState(false)
  const [showRestartModal, setShowRestartModal] = useState(false)
  const [previousModels, setPreviousModels] = useState<string[]>([])

  // Fetch server status on mount and periodically
  useEffect(() => {
    fetchServerStatus()
    const interval = setInterval(fetchServerStatus, 10000) // Every 10 seconds
    return () => clearInterval(interval)
  }, [])

  const handleLogoClick = () => {
    if (serverStatus.running) {
      // Server is running - show shutdown modal
      setShowRestartModal(false) // Ensure restart modal is closed
      setShowShutdownModal(true)
    } else {
      // Server is off - show restart modal
      setShowShutdownModal(false) // Ensure shutdown modal is closed
      setPreviousModels(serverStatus.loadedModels) // Use last known loaded models
      setShowRestartModal(true)
    }
  }

  const handleShutdownConfirm = async () => {
    try {
      const response = await fetch(`/api/v1/chat/ollama/server/shutdown`, {
        method: 'POST'
      })

      if (response.ok) {
        const data = await response.json()
        // Save models that were loaded before shutdown
        setPreviousModels(data.previously_loaded_models || [])
        // Close modal
        setShowShutdownModal(false)
        // Update server status
        await fetchServerStatus()
      } else {
        alert('Failed to shutdown Ollama server')
      }
    } catch (error) {
      console.error('Failed to shutdown Ollama:', error)
      alert('Failed to shutdown Ollama server')
    }
  }

  const handleRestartConfirm = async (reloadModels: boolean, modelsToLoad: string[]) => {
    try {
      const response = await fetch(
        `/api/v1/chat/ollama/server/restart?reload_models=${reloadModels}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ models_to_load: modelsToLoad })
        }
      )

      if (response.ok) {
        // Close modal
        setShowRestartModal(false)
        // Wait a moment for startup
        setTimeout(async () => {
          await fetchServerStatus()
        }, 3000)
      } else {
        alert('Failed to restart Ollama server')
      }
    } catch (error) {
      console.error('Failed to restart Ollama:', error)
      alert('Failed to restart Ollama server')
    }
  }

  return (
    <>
      <header className="glass border-b border-white/30 dark:border-gray-700/40">
        <div className="flex items-center justify-between py-3.5 px-6">
          {/* Left: Neutron Star Logo */}
          <div className="flex items-center gap-2">
            <button
              onClick={handleLogoClick}
              className="relative w-10 h-10 cursor-pointer group transition-transform hover:scale-110 active:scale-95"
              title={serverStatus.running ? `Ollama Server Running (${serverStatus.modelCount} models loaded) - Click to shutdown` : 'Ollama Server Stopped - Click to start'}
            >
              {/* Outer glow/radiation - shows server status */}
              <div className={`absolute -inset-1 rounded-full blur-sm transition-colors ${
                serverStatus.running
                  ? 'bg-green-400/40'
                  : 'bg-red-400/30'
              }`}></div>

              {/* Main star body - green when running, red when stopped */}
              <div className={`absolute inset-0 rounded-full shadow-lg transition-colors ${
                serverStatus.running
                  ? 'bg-gradient-radial from-green-200 via-green-500 to-green-800 group-hover:from-green-300 group-hover:via-green-600 group-hover:to-green-900'
                  : 'bg-gradient-radial from-gray-300 via-gray-500 to-gray-700 group-hover:from-green-200 group-hover:via-green-500 group-hover:to-green-800'
              }`}></div>

              {/* Surface detail - darker spots */}
              <div className={`absolute inset-2 rounded-full transition-colors ${
                serverStatus.running
                  ? 'bg-green-700/40'
                  : 'bg-gray-600/40 group-hover:bg-green-700/40'
              }`}></div>

              {/* Bright core */}
              <div className={`absolute inset-3 rounded-full transition-colors ${
                serverStatus.running
                  ? 'bg-gradient-to-br from-white via-green-100 to-green-300'
                  : 'bg-gradient-to-br from-gray-200 via-gray-300 to-gray-400 group-hover:from-white group-hover:via-green-100 group-hover:to-green-300'
              }`}></div>

              {/* Polar emission beams - only show when running */}
              {serverStatus.running && (
                <>
                  <div className="absolute top-0 left-1/2 -translate-x-1/2 w-0.5 h-2 bg-gradient-to-t from-green-300 to-transparent"></div>
                  <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-0.5 h-2 bg-gradient-to-b from-green-300 to-transparent"></div>
                </>
              )}

              {/* Rotating effect with magnetic field indicators */}
              <div className={`absolute inset-0 rounded-full border transition-colors ${
                serverStatus.running
                  ? 'border-green-400/50'
                  : 'border-gray-400/50 group-hover:border-green-400/50'
              }`}></div>
            </button>
          </div>

          {/* Center: Title */}
          <h1 className="absolute left-1/2 transform -translate-x-1/2 text-xl font-bold tracking-tight text-gray-900 dark:text-gray-100">
            OmniStudio
          </h1>

          {/* Right: Controls */}
          <div className="flex items-center gap-3">
            {/* Model Management Button */}
            <button
              onClick={() => setShowModelSidebar(true)}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400"
              title="Model Management (⌘M)"
            >
              <Cpu size={20} />
            </button>

            {/* Quick Chat */}
            <QuickChatDropdown />
          </div>
        </div>
      </header>

      {/* Model Management Sidebar */}
      <ModelManagementSidebar
        isOpen={showModelSidebar}
        onClose={() => setShowModelSidebar(false)}
      />

      {/* Ollama Server Control Modals */}
      <ShutdownModal
        isOpen={showShutdownModal}
        onClose={() => setShowShutdownModal(false)}
        onConfirm={handleShutdownConfirm}
        loadedModels={serverStatus.loadedModels}
      />

      <RestartModal
        isOpen={showRestartModal}
        onClose={() => setShowRestartModal(false)}
        onConfirm={handleRestartConfirm}
        previousModels={previousModels}
      />
    </>
  )
}
