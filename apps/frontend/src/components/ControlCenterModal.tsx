import { useState, useEffect } from 'react'
import { X, Activity, Cpu, HardDrive, Zap, Server, Database, Wifi, CheckCircle2, AlertCircle, XCircle, Loader2 } from 'lucide-react'

interface Metal4Stats {
  timestamp: string
  queues: {
    render: { active_buffers: number; total_submitted: number; total_completed: number; avg_encode_time_ms: number }
    ml: { active_buffers: number; total_submitted: number; total_completed: number; avg_encode_time_ms: number }
    blit: { active_buffers: number; total_submitted: number; total_completed: number; avg_encode_time_ms: number }
  }
  events: {
    frame_counter: number
    embed_counter: number
    rag_counter: number
  }
  memory: {
    heap_used_mb: number
    heap_total_mb: number
    heap_utilization_pct: number
    pressure: string
  }
  performance: {
    frame_time_ms: number
    fps: number
    gpu_util_pct: number
    overlapped_ops: number
  }
  operations: {
    embeddings: number
    transcriptions: number
    sql_queries: number
    render_frames: number
    blit_transfers: number
  }
}

interface ServiceHealth {
  status: 'healthy' | 'degraded' | 'down'
  message?: string
  latency_ms?: number
  details?: Record<string, any>
}

interface SystemHealth {
  status: 'healthy' | 'degraded' | 'down'
  timestamp: string
  services: {
    api: ServiceHealth
    database: ServiceHealth
    ollama?: ServiceHealth
    embeddings?: ServiceHealth
    p2p?: ServiceHealth
    vault?: ServiceHealth
  }
  system: {
    cpu_percent: number
    memory_percent: number
    disk_usage_percent?: number
  }
}

interface ControlCenterModalProps {
  isOpen: boolean
  onClose: () => void
}

export function ControlCenterModal({ isOpen, onClose }: ControlCenterModalProps) {
  const [metal4Stats, setMetal4Stats] = useState<Metal4Stats | null>(null)
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null)
  const [isLoadingMetal, setIsLoadingMetal] = useState(false)
  const [isLoadingHealth, setIsLoadingHealth] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Close on ESC
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        onClose()
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('keydown', handleEscape)
    }
  }, [isOpen, onClose])

  // Fetch data when opened
  useEffect(() => {
    if (isOpen) {
      fetchAllData()
      // Auto-refresh every 3 seconds while open
      const interval = setInterval(fetchAllData, 3000)
      return () => clearInterval(interval)
    }
  }, [isOpen])

  const fetchAllData = async () => {
    await Promise.all([
      fetchMetal4Stats(),
      fetchSystemHealth()
    ])
  }

  const fetchMetal4Stats = async () => {
    setIsLoadingMetal(true)
    try {
      const response = await fetch('/api/v1/monitoring/metal4')
      if (response.ok) {
        const data = await response.json()
        setMetal4Stats(data)
      }
    } catch (err) {
      console.warn('Metal4 stats unavailable:', err)
    } finally {
      setIsLoadingMetal(false)
    }
  }

  const fetchSystemHealth = async () => {
    setIsLoadingHealth(true)
    setError(null)
    try {
      const response = await fetch('/api/v1/monitoring/health')
      if (!response.ok) {
        throw new Error('Failed to fetch system health')
      }
      const data = await response.json()
      setSystemHealth(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch health')
    } finally {
      setIsLoadingHealth(false)
    }
  }

  const getStatusColor = (status: ServiceHealth['status']) => {
    switch (status) {
      case 'healthy':
        return 'text-green-500'
      case 'degraded':
        return 'text-yellow-500'
      case 'down':
        return 'text-red-500'
      default:
        return 'text-gray-400'
    }
  }

  const getStatusIcon = (status: ServiceHealth['status']) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle2 className="w-4 h-4" />
      case 'degraded':
        return <AlertCircle className="w-4 h-4" />
      case 'down':
        return <XCircle className="w-4 h-4" />
      default:
        return <Loader2 className="w-4 h-4 animate-spin" />
    }
  }

  const getPressureColor = (pressure: string) => {
    switch (pressure?.toLowerCase()) {
      case 'low':
        return 'text-green-500'
      case 'medium':
        return 'text-yellow-500'
      case 'high':
        return 'text-red-500'
      default:
        return 'text-gray-400'
    }
  }

  const getPressureLabel = (pressure: string) => {
    switch (pressure?.toLowerCase()) {
      case 'low':
        return 'Normal'
      case 'medium':
        return 'Medium'
      case 'high':
        return 'High'
      default:
        return pressure
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
      />

      {/* Modal */}
      <div className="relative w-full max-w-5xl max-h-[90vh] bg-white dark:bg-gray-900 rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-gray-200 dark:border-gray-700">
        {/* Header - macOS 26 style */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-gray-800 dark:to-gray-850">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-white dark:bg-gray-900 rounded-xl shadow-sm">
              <Activity className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                Control Center
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                System monitoring & diagnostics
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-white/50 dark:hover:bg-gray-800/50 transition-colors"
          >
            <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {error && (
            <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <div className="flex items-center gap-2 text-red-700 dark:text-red-400">
                <AlertCircle className="w-5 h-5" />
                <span className="font-medium">{error}</span>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* System Health */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-3">
                <Server className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  System Health
                </h3>
              </div>

              {!systemHealth ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                </div>
              ) : (
                <>
                  {/* Services */}
                  <div className="space-y-2">
                    {Object.entries(systemHealth.services).map(([name, service]) => (
                      <div
                        key={name}
                        className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                      >
                        <div className="flex items-center gap-3">
                          <div className={getStatusColor(service.status)}>
                            {getStatusIcon(service.status)}
                          </div>
                          <div>
                            <div className="text-sm font-medium text-gray-900 dark:text-gray-100 capitalize">
                              {name}
                            </div>
                            {service.message && (
                              <div className="text-xs text-gray-500 dark:text-gray-400">
                                {service.message}
                              </div>
                            )}
                          </div>
                        </div>
                        {service.latency_ms !== undefined && (
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {service.latency_ms.toFixed(0)}ms
                          </span>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* System Resources */}
                  <div className="mt-4 p-4 bg-gradient-to-br from-blue-50 to-purple-50 dark:from-gray-800 dark:to-gray-850 rounded-lg">
                    <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                      System Resources
                    </div>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Cpu className="w-4 h-4 text-blue-500" />
                          <span className="text-sm text-gray-700 dark:text-gray-300">CPU</span>
                        </div>
                        <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                          {systemHealth.system.cpu_percent.toFixed(1)}%
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <HardDrive className="w-4 h-4 text-purple-500" />
                          <span className="text-sm text-gray-700 dark:text-gray-300">Memory</span>
                        </div>
                        <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                          {systemHealth.system.memory_percent.toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Metal 4 Performance */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-3">
                <Zap className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Metal 4 GPU
                </h3>
              </div>

              {!metal4Stats ? (
                <div className="flex items-center justify-center py-12">
                  <div className="text-center">
                    <Loader2 className="w-6 h-6 animate-spin text-gray-400 mx-auto mb-2" />
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Initializing GPU monitoring...
                    </p>
                  </div>
                </div>
              ) : (
                <>
                  {/* GPU Performance */}
                  <div className="p-4 bg-gradient-to-br from-green-50 to-blue-50 dark:from-gray-800 dark:to-gray-850 rounded-lg">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">FPS</div>
                        <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                          {metal4Stats.performance.fps.toFixed(1)}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Frame Time</div>
                        <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                          {metal4Stats.performance.frame_time_ms.toFixed(1)}ms
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">GPU Util</div>
                        <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                          {metal4Stats.performance.gpu_util_pct.toFixed(1)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Parallel Ops</div>
                        <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                          {metal4Stats.performance.overlapped_ops}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Memory */}
                  <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Unified Memory
                      </span>
                      <span className={`text-sm font-semibold ${getPressureColor(metal4Stats.memory.pressure)}`}>
                        {getPressureLabel(metal4Stats.memory.pressure)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600 dark:text-gray-400">
                        {metal4Stats.memory.heap_used_mb.toFixed(0)} MB / {metal4Stats.memory.heap_total_mb.toFixed(0)} MB
                      </span>
                      <span className="font-semibold text-gray-900 dark:text-gray-100">
                        {metal4Stats.memory.heap_utilization_pct.toFixed(1)}%
                      </span>
                    </div>
                  </div>

                  {/* Command Queues */}
                  <div className="space-y-2">
                    <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Command Queues
                    </div>
                    {Object.entries(metal4Stats.queues).map(([name, queue]) => (
                      <div
                        key={name}
                        className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded"
                      >
                        <div className="text-sm text-gray-700 dark:text-gray-300 capitalize">
                          {name}
                        </div>
                        <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                          <span>Active: {queue.active_buffers}</span>
                          <span>Avg: {queue.avg_encode_time_ms.toFixed(1)}ms</span>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Operation Counters */}
                  <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                      Operations
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      {Object.entries(metal4Stats.operations).map(([name, count]) => (
                        <div key={name} className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400 capitalize">
                            {name.replace('_', ' ')}:
                          </span>
                          <span className="font-semibold text-gray-900 dark:text-gray-100">
                            {count}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/50">
          <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
            <span>Auto-refreshes every 3 seconds</span>
            <span>
              Last updated: {systemHealth?.timestamp ? new Date(systemHealth.timestamp).toLocaleTimeString() : 'Never'}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
