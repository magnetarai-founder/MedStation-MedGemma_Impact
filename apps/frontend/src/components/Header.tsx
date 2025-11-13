import { useState, useEffect } from 'react'
import { AlertTriangle, Activity, Terminal } from 'lucide-react'
import { ControlCenterModal } from './ControlCenterModal'
import { ModelManagementSidebar } from './ModelManagementSidebar'
import { ModelDownloadsManager } from './ModelDownloadsManager'
import { QuickActionsModal } from './QuickActionsModal'
import { SessionTimelineModal } from './SessionTimelineModal'
import { SearchSessionsModal } from './SearchSessionsModal'
import { ContextBadge } from './ContextBadge'
import { useOllamaStore } from '../stores/ollamaStore'
import { useChatStore } from '../stores/chatStore'
import { useTeamStore } from '../stores/teamStore'
import { useUserStore } from '../stores/userStore'
import { ShutdownModal, RestartModal } from './OllamaServerModals'
import { PanicModeModal } from './PanicModeModal'
import { metal4StatsService } from '../services/metal4StatsService'
import { ActionsContext } from '../lib/actionsRegistry'
import { authFetch } from '../lib/api'
import { showToast } from '../lib/toast'

interface HeaderProps {
  onOpenServerControls: () => void
}

export function Header({ onOpenServerControls }: HeaderProps) {
  const [showModelSidebar, setShowModelSidebar] = useState(false)
  const [showDownloadsManager, setShowDownloadsManager] = useState(false)
  const [pendingDownloadModel, setPendingDownloadModel] = useState<string | undefined>(undefined)
  const [showQuickActions, setShowQuickActions] = useState(false)
  const [showTimeline, setShowTimeline] = useState(false)
  const [showSearchModal, setShowSearchModal] = useState(false)
  const { serverStatus, fetchServerStatus } = useOllamaStore()
  const { activeChatId, getActiveSession, createSession, setActiveChatId } = useChatStore()
  const { currentTeam } = useTeamStore()
  const { user } = useUserStore()
  const [showShutdownModal, setShowShutdownModal] = useState(false)
  const [showRestartModal, setShowRestartModal] = useState(false)
  const [previousModels, setPreviousModels] = useState<string[]>([])
  const [showPanicConfirm, setShowPanicConfirm] = useState(false)
  const [showControlCenter, setShowControlCenter] = useState(false)
  const [activeTerminals, setActiveTerminals] = useState(0)
  const [activeQueues, setActiveQueues] = useState(0)
  const [gpuActive, setGpuActive] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [pausedSecondsRemaining, setPausedSecondsRemaining] = useState(0)
  const [queueLatency, setQueueLatency] = useState<number | null>(null)
  const [oldestJobAge, setOldestJobAge] = useState<number | null>(null)
  const [gpuUtil, setGpuUtil] = useState<number | null>(null)
  const [gpuTemp, setGpuTemp] = useState<number | null>(null)
  const [gpuMemUsed, setGpuMemUsed] = useState<number | null>(null)
  const [gpuMemTotal, setGpuMemTotal] = useState<number | null>(null)
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

      // Check if GPU is active (utilization > 0)
      const utilization = stats.gpu?.utilization ?? 0
      setGpuActive(utilization > 0)

      // Update queue latency and oldest job age (Sprint 3)
      setQueueLatency(stats.queue_latency_ms ?? null)
      setOldestJobAge(stats.oldest_job_age_ms ?? null)

      // Update GPU diagnostics (Sprint 4)
      setGpuUtil(stats.gpu?.utilization ?? null)
      setGpuTemp(stats.gpu?.temperature ?? null)
      setGpuMemUsed(stats.gpu?.memory_used_mb ?? null)
      setGpuMemTotal(stats.gpu?.memory_total_mb ?? null)
    })

    return unsubscribe
  }, [])

  // Check paused state periodically
  useEffect(() => {
    const checkPausedState = () => {
      const paused = metal4StatsService.isInCooldown()
      const remaining = metal4StatsService.getCooldownRemainingSeconds()
      setIsPaused(paused)
      setPausedSecondsRemaining(remaining)
    }

    // Check immediately
    checkPausedState()

    // Check every second while paused
    const interval = setInterval(checkPausedState, 1000)
    return () => clearInterval(interval)
  }, [])

  // Listen for custom event to open Model Management sidebar
  useEffect(() => {
    const handleOpenModelManagement = () => {
      setShowModelSidebar(true)
    }

    window.addEventListener('openModelManagement', handleOpenModelManagement)
    return () => window.removeEventListener('openModelManagement', handleOpenModelManagement)
  }, [])

  // Listen for custom event to open Downloads Manager
  useEffect(() => {
    const handleOpenDownloadsManager = ((event: CustomEvent) => {
      setPendingDownloadModel(event.detail?.model)
      setShowDownloadsManager(true)
    }) as EventListener

    window.addEventListener('openDownloadsManager', handleOpenDownloadsManager)
    return () => window.removeEventListener('openDownloadsManager', handleOpenDownloadsManager)
  }, [])

  // Listen for Cmd/Ctrl+K to open Quick Actions (Sprint 5)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setShowQuickActions(true)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
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

  // Quick Actions handlers (Sprint 5 Theme D)
  const handleNewSession = async () => {
    try {
      const response = await authFetch('/api/v1/chat/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: 'New Session',
          team_id: currentTeam?.team_id || null
        })
      })

      if (response.ok) {
        const data = await response.json()
        const newSessionId = data.chat_id

        // Add to store and set as active
        createSession(newSessionId, 'New Session', currentTeam?.team_id || null)
        setActiveChatId(newSessionId)

        showToast.success('New session created')
      }
    } catch (error) {
      console.error('Failed to create session:', error)
      showToast.error('Failed to create new session')
    }
  }

  const handleOpenDownloads = () => {
    setShowDownloads(true)
  }

  const handleViewTimeline = () => {
    if (!activeChatId) {
      showToast.error('No active session to view timeline')
      return
    }
    setShowTimeline(true)
  }

  const handleSwitchTeam = () => {
    setShowTeamSwitcher(true)
  }

  const handleExportPermissions = async () => {
    try {
      const response = await authFetch('/api/v1/permissions/export')
      if (response.ok) {
        const data = await response.json()

        // Download as JSON file
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `permissions-export-${new Date().toISOString().split('T')[0]}.json`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)

        showToast.success('Permissions exported successfully')
      }
    } catch (error) {
      console.error('Failed to export permissions:', error)
      showToast.error('Failed to export permissions')
    }
  }

  const handleSearchSessions = () => {
    setShowSearchModal(true)
  }

  // Build ActionsContext for QuickActionsModal
  const activeSession = activeChatId ? getActiveSession(activeChatId) : null
  const actionsContext: ActionsContext = {
    activeSessionId: activeChatId || undefined,
    activeSessionTitle: activeSession?.title || undefined,
    teams: currentTeam ? [{ id: currentTeam.team_id, name: currentTeam.team_name }] : [],
    hasPermissions: user?.role === 'admin',
    onNewSession: handleNewSession,
    onOpenDownloads: handleOpenDownloads,
    onViewTimeline: handleViewTimeline,
    onSwitchTeam: handleSwitchTeam,
    onExportPermissions: handleExportPermissions,
    onSearchSessions: handleSearchSessions
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

            {/* Control Center (includes Performance Monitor) with indicators */}
            <div className="flex items-center gap-2">
              {/* GPU Badge (Sprint 4) */}
              {gpuUtil !== null && gpuUtil > 0 && (
                <div
                  className="flex items-center gap-1 px-1.5 py-0.5 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 rounded text-xs cursor-help"
                  title={`GPU: ${Math.round(gpuUtil)}%${gpuTemp !== null ? ` • ${Math.round(gpuTemp)}°C` : ''}${gpuMemUsed !== null && gpuMemTotal !== null ? ` • ${Math.round(gpuMemUsed)}MB / ${Math.round(gpuMemTotal)}MB` : ''}`}
                  aria-label={`GPU utilization ${Math.round(gpuUtil)} percent`}
                  role="status"
                >
                  <span className="text-[10px] font-medium">GPU:</span>
                  <span className="text-[10px]">{Math.round(gpuUtil)}%</span>
                </div>
              )}

              {/* Queue Latency Badge (Sprint 3) */}
              {queueLatency !== null && queueLatency > 0 && (
                <div
                  className="flex items-center gap-1 px-1.5 py-0.5 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded text-xs cursor-help"
                  title={`Queue Latency: ${queueLatency.toFixed(0)}ms${queueLatency > 100 ? ' (High)' : queueLatency > 50 ? ' (Moderate)' : ' (Low)'}`}
                  aria-label={`Queue latency ${queueLatency} milliseconds`}
                  role="status"
                >
                  <span className="text-[10px] font-medium">QL:</span>
                  <span className="text-[10px]">{queueLatency.toFixed(0)}ms</span>
                </div>
              )}

              {/* Oldest Job Age Badge (Sprint 3) */}
              {oldestJobAge !== null && oldestJobAge > 0 && (
                <div
                  className="flex items-center gap-1 px-1.5 py-0.5 bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300 rounded text-xs cursor-help"
                  title={`Oldest Job: ${(oldestJobAge / 1000).toFixed(1)}s${oldestJobAge > 10000 ? ' (Stale)' : oldestJobAge > 5000 ? ' (Aging)' : ' (Fresh)'}`}
                  aria-label={`Oldest job age ${(oldestJobAge / 1000).toFixed(1)} seconds`}
                  role="status"
                >
                  <span className="text-[10px] font-medium">Job:</span>
                  <span className="text-[10px]">{(oldestJobAge / 1000).toFixed(1)}s</span>
                </div>
              )}

              {/* GPU Active Indicator */}
              {gpuActive && (
                <div
                  className="w-2 h-2 bg-green-500 rounded-full animate-pulse"
                  title="GPU Active"
                  aria-label="GPU is currently active"
                  role="status"
                />
              )}

              {/* Paused Indicator (429 backoff) */}
              {isPaused && (
                <div
                  className="flex items-center gap-1 px-2 py-0.5 bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 rounded text-xs"
                  title={`Rate limited - resuming in ${pausedSecondsRemaining}s`}
                  aria-label={`Monitoring paused due to rate limit, resuming in ${pausedSecondsRemaining} seconds`}
                  role="status"
                  aria-live="polite"
                >
                  <span className="text-[10px]">⏸</span>
                  <span className="text-[10px]">{pausedSecondsRemaining}s</span>
                </div>
              )}

              <div className="relative">
                <button
                  onClick={() => setShowControlCenter(true)}
                  className="p-2 hover:bg-blue-100 dark:hover:bg-blue-900/20 rounded-lg transition-colors text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
                  title={activeQueues > 0 ? `Control Center - ${activeQueues} active GPU queue(s)` : "Control Center (System Monitoring)"}
                  aria-label={activeQueues > 0 ? `Open Control Center, ${activeQueues} active GPU queues` : "Open Control Center for system monitoring"}
                >
                  <Activity size={20} />
                </button>
                {activeQueues > 0 && (
                  <div
                    className="absolute -top-1 -right-1 w-4 h-4 bg-green-500 rounded-full flex items-center justify-center border-2 border-white dark:border-gray-900 animate-pulse"
                    title={`${activeQueues} active GPU queue(s)`}
                    aria-label={`${activeQueues} active GPU queue${activeQueues > 1 ? 's' : ''}`}
                    role="status"
                  >
                    <span className="text-[9px] font-bold text-white" aria-hidden="true">{activeQueues}</span>
                  </div>
                )}
              </div>
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

      {/* Model Downloads Manager */}
      {showDownloadsManager && (
        <ModelDownloadsManager
          onClose={() => {
            setShowDownloadsManager(false)
            setPendingDownloadModel(undefined)
          }}
          initialModel={pendingDownloadModel}
        />
      )}

      {/* Quick Actions Panel (Sprint 5 Theme D) */}
      {showQuickActions && (
        <QuickActionsModal
          context={actionsContext}
          onClose={() => setShowQuickActions(false)}
        />
      )}

      {/* Session Timeline Modal */}
      {showTimeline && activeChatId && (
        <SessionTimelineModal
          sessionId={activeChatId}
          onClose={() => setShowTimeline(false)}
        />
      )}

      {/* Search Sessions Modal */}
      {showSearchModal && (
        <SearchSessionsModal
          onClose={() => setShowSearchModal(false)}
        />
      )}
    </>
  )
}
