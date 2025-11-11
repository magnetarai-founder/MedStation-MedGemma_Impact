/**
 * System Health Dashboard
 *
 * "The Lord is my strength and my shield" - Psalm 28:7
 *
 * Comprehensive system health monitoring dashboard integrating:
 * - Health check status (/health)
 * - Detailed diagnostics (/diagnostics)
 * - Prometheus metrics visualization
 * - Metal 4 GPU status
 * - Component health cards
 *
 * Features:
 * - Real-time health monitoring
 * - Auto-refresh every 30 seconds
 * - Visual status indicators
 * - Detailed component breakdowns
 * - Performance metrics
 */

import { useState, useEffect } from 'react'
import {
  Activity,
  Cpu,
  HardDrive,
  Database,
  Zap,
  AlertCircle,
  CheckCircle,
  RefreshCw,
  Server,
  TrendingUp,
  Clock,
  BarChart3
} from 'lucide-react'

interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy'
  timestamp: string
  uptime_seconds: number
  checks: {
    database: {
      status: string
      available: boolean
    }
    memory: {
      status: string
      usage_percent: number
    }
    disk: {
      status: string
      usage_percent: number
    }
  }
  response_time_ms: number
}

interface Diagnostics {
  status: 'healthy' | 'degraded' | 'unhealthy'
  timestamp: string
  uptime_seconds: number
  cached: boolean
  cache_age_seconds?: number
  components: {
    database: ComponentHealth
    metal4_engine: ComponentHealth
    metal4_sql: ComponentHealth
    tensor_ops: ComponentHealth
    metalfx_renderer: ComponentHealth
  }
  system: SystemInfo
  metal4: Metal4Info
  performance: PerformanceInfo
  response_time_ms: number
}

interface ComponentHealth {
  status: 'healthy' | 'degraded' | 'unhealthy' | 'unavailable'
  available: boolean
  [key: string]: any
}

interface SystemInfo {
  platform: string
  platform_release: string
  architecture: string
  cpu_count: number
  cpu_percent: number
  memory_total_gb: number
  memory_used_gb: number
  memory_percent: number
  disk_total_gb: number
  disk_used_gb: number
  disk_percent: number
}

interface Metal4Info {
  available: boolean
  version?: number
  device_name?: string | null
  supports_unified_memory?: boolean
  recommended_heap_size_mb?: number
  error?: string
}

interface PerformanceInfo {
  uptime_seconds: number
  uptime_hours: number
}

export default function SystemHealthDashboard() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [diagnostics, setDiagnostics] = useState<Diagnostics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date())

  useEffect(() => {
    fetchHealth()
    fetchDiagnostics()

    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      if (autoRefresh) {
        fetchHealth()
        fetchDiagnostics()
      }
    }, 30000)

    return () => clearInterval(interval)
  }, [autoRefresh])

  const fetchHealth = async () => {
    try {
      const response = await fetch('/health')
      if (!response.ok) throw new Error('Health check failed')
      const data = await response.json()
      setHealth(data)
      setLastRefresh(new Date())
    } catch (err: any) {
      console.error('Failed to fetch health:', err)
      setError(err.message)
    }
  }

  const fetchDiagnostics = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('/diagnostics')
      if (!response.ok) throw new Error('Diagnostics failed')
      const data = await response.json()
      setDiagnostics(data)
    } catch (err: any) {
      console.error('Failed to fetch diagnostics:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = () => {
    fetchHealth()
    fetchDiagnostics()
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-green-500'
      case 'degraded': return 'text-yellow-500'
      case 'unhealthy': return 'text-red-500'
      case 'unavailable': return 'text-gray-400'
      default: return 'text-gray-500'
    }
  }

  const getStatusBgColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'bg-green-500/10 border-green-500/20'
      case 'degraded': return 'bg-yellow-500/10 border-yellow-500/20'
      case 'unhealthy': return 'bg-red-500/10 border-red-500/20'
      case 'unavailable': return 'bg-gray-500/10 border-gray-500/20'
      default: return 'bg-gray-500/10 border-gray-500/20'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'degraded': return <AlertCircle className="w-5 h-5 text-yellow-500" />
      case 'unhealthy': return <AlertCircle className="w-5 h-5 text-red-500" />
      default: return <Activity className="w-5 h-5 text-gray-400" />
    }
  }

  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    if (hours > 24) {
      const days = Math.floor(hours / 24)
      return `${days}d ${hours % 24}h`
    }
    return `${hours}h ${minutes}m`
  }

  if (loading && !diagnostics) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-6 h-6 animate-spin text-blue-500" />
        <span className="ml-2 text-gray-400">Loading system diagnostics...</span>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <Activity className="w-6 h-6 text-blue-500" />
            System Health
          </h2>
          <p className="text-sm text-gray-400 mt-1">
            Real-time monitoring and diagnostics
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-sm text-gray-400">
            Last updated: {lastRefresh.toLocaleTimeString()}
          </div>
          <label className="flex items-center gap-2 text-sm text-gray-400">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded"
            />
            Auto-refresh
          </label>
          <button
            onClick={handleRefresh}
            className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Overall Health Status */}
      {health && (
        <div className={`p-6 rounded-lg border ${getStatusBgColor(health.status)}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {getStatusIcon(health.status)}
              <div>
                <h3 className="text-lg font-semibold text-white capitalize">
                  System {health.status}
                </h3>
                <p className="text-sm text-gray-400">
                  Response time: {health.response_time_ms.toFixed(1)}ms
                </p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm text-gray-400">Uptime</div>
              <div className="text-xl font-bold text-white">
                {formatUptime(health.uptime_seconds)}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Quick Stats Grid */}
      {diagnostics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* CPU */}
          <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
            <div className="flex items-center gap-2 mb-2">
              <Cpu className="w-5 h-5 text-blue-500" />
              <h4 className="font-semibold text-white">CPU</h4>
            </div>
            <div className="text-2xl font-bold text-white">
              {diagnostics.system.cpu_percent.toFixed(1)}%
            </div>
            <div className="text-sm text-gray-400">
              {diagnostics.system.cpu_count} cores
            </div>
          </div>

          {/* Memory */}
          <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
            <div className="flex items-center gap-2 mb-2">
              <Server className="w-5 h-5 text-green-500" />
              <h4 className="font-semibold text-white">Memory</h4>
            </div>
            <div className="text-2xl font-bold text-white">
              {diagnostics.system.memory_percent.toFixed(1)}%
            </div>
            <div className="text-sm text-gray-400">
              {diagnostics.system.memory_used_gb.toFixed(1)} / {diagnostics.system.memory_total_gb.toFixed(1)} GB
            </div>
          </div>

          {/* Disk */}
          <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
            <div className="flex items-center gap-2 mb-2">
              <HardDrive className="w-5 h-5 text-purple-500" />
              <h4 className="font-semibold text-white">Disk</h4>
            </div>
            <div className="text-2xl font-bold text-white">
              {diagnostics.system.disk_percent.toFixed(1)}%
            </div>
            <div className="text-sm text-gray-400">
              {diagnostics.system.disk_used_gb.toFixed(1)} / {diagnostics.system.disk_total_gb.toFixed(1)} GB
            </div>
          </div>

          {/* Response Time */}
          <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-5 h-5 text-yellow-500" />
              <h4 className="font-semibold text-white">Response Time</h4>
            </div>
            <div className="text-2xl font-bold text-white">
              {diagnostics.response_time_ms.toFixed(1)}ms
            </div>
            <div className="text-sm text-gray-400">
              {diagnostics.cached ? `Cached (${diagnostics.cache_age_seconds}s ago)` : 'Fresh'}
            </div>
          </div>
        </div>
      )}

      {/* Metal 4 GPU Status */}
      {diagnostics?.metal4 && (
        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-5 h-5 text-yellow-500" />
            <h3 className="text-lg font-semibold text-white">Metal 4 GPU Acceleration</h3>
          </div>
          {diagnostics.metal4.available ? (
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-400">Device:</span>
                <span className="text-white">{diagnostics.metal4.device_name || 'Unknown'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Metal Version:</span>
                <span className="text-white">Metal {diagnostics.metal4.version}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Unified Memory:</span>
                <span className="text-white">
                  {diagnostics.metal4.supports_unified_memory ? '✓ Enabled' : '✗ Not available'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Heap Size:</span>
                <span className="text-white">{diagnostics.metal4.recommended_heap_size_mb} MB</span>
              </div>
            </div>
          ) : (
            <div className="text-gray-400">
              {diagnostics.metal4.error || 'Metal 4 GPU not available'}
            </div>
          )}
        </div>
      )}

      {/* Component Health */}
      {diagnostics && (
        <div>
          <h3 className="text-lg font-semibold text-white mb-4">Component Health</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(diagnostics.components).map(([name, component]) => (
              <div
                key={name}
                className={`p-4 rounded-lg border ${getStatusBgColor(component.status)}`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Database className="w-5 h-5 text-gray-400" />
                    <h4 className="font-semibold text-white capitalize">
                      {name.replace(/_/g, ' ')}
                    </h4>
                  </div>
                  {getStatusIcon(component.status)}
                </div>
                <div className="text-sm text-gray-400">
                  Status: <span className={`capitalize ${getStatusColor(component.status)}`}>
                    {component.status}
                  </span>
                </div>
                {component.available !== undefined && (
                  <div className="text-sm text-gray-400">
                    Available: {component.available ? 'Yes' : 'No'}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* System Information */}
      {diagnostics && (
        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">System Information</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <div className="text-sm text-gray-400">Platform</div>
              <div className="text-white">{diagnostics.system.platform} {diagnostics.system.platform_release}</div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Architecture</div>
              <div className="text-white">{diagnostics.system.architecture}</div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Python Version</div>
              <div className="text-white">{diagnostics.system.python_version}</div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Uptime</div>
              <div className="text-white">{formatUptime(diagnostics.uptime_seconds)}</div>
            </div>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
          <div className="flex items-center gap-2 text-red-500">
            <AlertCircle className="w-5 h-5" />
            <span className="font-semibold">Error</span>
          </div>
          <p className="text-sm text-gray-400 mt-2">{error}</p>
        </div>
      )}
    </div>
  )
}
