import { useState, useEffect } from 'react'
import { AlertTriangle, Activity, Terminal } from 'lucide-react'
import { ControlCenterModal } from './ControlCenterModal'
import { ModelManagementSidebar } from './ModelManagementSidebar'
import { ContextBadge } from './ContextBadge'
import { useOllamaStore } from '../stores/ollamaStore'
import { ShutdownModal, RestartModal } from './OllamaServerModals'
import { PanicModeModal } from './PanicModeModal'
import { metal4StatsService } from '../services/metal4StatsService'

interface HeaderProps {
  onOpenServerControls: () => void
}

export function Header({ onOpenServerControls }: HeaderProps) {
  const [showModelSidebar, setShowModelSidebar] = useState(false)
  const { serverStatus, fetchServerStatus } = useOllamaStore()
  const [showShutdownModal, setShowShutdownModal] = useState(false)
  const [showRestartModal, setShowRestartModal] = useState(false)
  const [previousModels, setPreviousModels] = useState<string[]>([])
  const [showPanicConfirm, setShowPanicConfirm] = useState(false)
  const [showControlCenter, setShowControlCenter] = useState(false)
  const [activeTerminals, setActiveTerminals] = useState(0)
  const [activeQueues, setActiveQueues] = useState(0)
  const MAX_TERMINALS = 3

  // Fetch server status on mount and periodically
  useEffect(() => {
    fetchServerStatus()
    const interval = setInterval(fetchServerStatus, 60000) // Every 60 seconds (reduced from 10s to minimize noise)
    return () => clearInterval(interval)
  }, [])

  // Subscribe to shared Metal4 stats service (prevents duplicate polling)
  useEffect(() => {
    const unsubscribe = metal4StatsService.subscribe((stats) => {
      if (!stats) {
        // Error or rate limited - keep current value
        return
      }

      // Sum active_buffers across all queues
      let total = 0
      if (stats.queues) {
        for (const queue of Object.values(stats.queues)) {
          if (typeof queue === 'object' && queue !== null && 'active_buffers' in queue) {
            total += (queue as { active_buffers: number }).active_buffers || 0
          }
        }
      }

      setActiveQueues(total)
    })

    return unsubscribe
  }, [])

  const handleLogoClick = () => {
    // Toggle Model Management sidebar
    setShowModelSidebar(!showModelSidebar)
  }

  const handleSpawnTerminal = async () => {
    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch('/api/v1/terminal/spawn-system', {
        method: 'POST',
        credentials: 'include',
        headers: {
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        }
      })

      if (!response.ok) {
        let detail = 'Failed to spawn terminal'
        try {
          const data = await response.json()
          if (data && (data as any).detail) detail = (data as any).detail
        } catch {}
        alert(detail)
        return
      }

      const data = await response.json()
      setActiveTerminals(data.active_terminals)
    } catch (error) {
      console.error('Error spawning terminal:', error)
      alert('Failed to spawn terminal')
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
      <header className="glass border-b border-white/20 dark:border-gray-700/30 relative z-50 bg-gradient-to-r from-blue-50/80 via-purple-50/80 to-pink-50/80 dark:from-gray-900/80 dark:via-gray-850/80 dark:to-gray-900/80 backdrop-blur-xl">
        <div className="flex items-center justify-between py-3.5 px-6">
          {/* Left: Neutron Star Logo */}
          <div className="flex items-center gap-2">
            <button
              onClick={handleLogoClick}
              className="relative w-10 h-10 cursor-pointer group transition-transform hover:scale-110 active:scale-95"
              title="Model Management"
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
            ElohimOS
          </h1>

          {/* Right: Controls */}
          <div className="flex items-center gap-3">
            {/* Context Badge */}
            <ContextBadge size="sm" />

            {/* Terminal Button + Counter */}
            <div className="flex items-center gap-2">
              <button
                onClick={handleSpawnTerminal}
                className="p-2 hover:bg-purple-100 dark:hover:bg-purple-900/20 rounded-lg transition-colors text-gray-600 dark:text-gray-400 hover:text-purple-600 dark:hover:text-purple-400"
                title="Open System Terminal"
              >
                <Terminal size={20} />
              </button>

              {/* Terminal Counter */}
              <div className="text-xs font-medium text-gray-500 dark:text-gray-400 min-w-[2.5rem]">
                {activeTerminals}/{MAX_TERMINALS}
              </div>
            </div>

            {/* Control Center (includes Performance Monitor) with Queue Badge */}
            <div className="relative">
              <button
                onClick={() => setShowControlCenter(true)}
                className="p-2 hover:bg-blue-100 dark:hover:bg-blue-900/20 rounded-lg transition-colors text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
                title={activeQueues > 0 ? `Control Center - ${activeQueues} active GPU queue(s)` : "Control Center (System Monitoring)"}
              >
                <Activity size={20} />
              </button>
              {activeQueues > 0 && (
                <div
                  className="absolute -top-1 -right-1 w-4 h-4 bg-green-500 rounded-full flex items-center justify-center border-2 border-white dark:border-gray-900 animate-pulse"
                  title={`${activeQueues} active GPU queue(s)`}
                >
                  <span className="text-[9px] font-bold text-white">{activeQueues}</span>
                </div>
              )}
            </div>

            {/* PANIC BUTTON (Emergency Data Wipe) */}
            <button
              onClick={() => setShowPanicConfirm(true)}
              className="p-2 hover:bg-red-100 dark:hover:bg-red-900/20 rounded-lg transition-colors text-gray-600 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400"
              title="🚨 PANIC MODE (Emergency Data Wipe)"
            >
              <AlertTriangle size={20} />
            </button>
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

      {/* Panic Mode Modal */}
      <PanicModeModal
        isOpen={showPanicConfirm}
        onClose={() => setShowPanicConfirm(false)}
      />

      {/* Control Center Modal */}
      <ControlCenterModal
        isOpen={showControlCenter}
        onClose={() => setShowControlCenter(false)}
      />
    </>
  )
}
