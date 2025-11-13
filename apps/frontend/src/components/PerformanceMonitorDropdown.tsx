import { useState, useEffect, useRef } from 'react'
import { Activity, X, TrendingUp, Cpu, Zap, Thermometer } from 'lucide-react'

interface PerformanceStats {
  current?: {
    tokens_per_second?: number
    cpu_percent?: number
    memory_percent?: number
    thermal_state?: string
  }
  averages?: {
    tokens_per_second?: number
    cpu_percent?: number
  }
  uptime_seconds?: number
}

interface PerformanceMonitorDropdownProps {
  isOpen?: boolean
  onToggle?: () => void
}

export function PerformanceMonitorDropdown({ isOpen: controlledIsOpen, onToggle }: PerformanceMonitorDropdownProps = {}) {
  const [internalIsOpen, setInternalIsOpen] = useState(false)
  const isOpen = controlledIsOpen !== undefined ? controlledIsOpen : internalIsOpen
  const [stats, setStats] = useState<PerformanceStats | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const handleToggle = () => {
    if (onToggle) {
      onToggle()
    } else {
      setInternalIsOpen(!internalIsOpen)
    }
  }

  const handleClose = () => {
    if (onToggle) {
      onToggle()
    } else {
      setInternalIsOpen(false)
    }
  }

  // Close on ESC
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        handleClose()
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('keydown', handleEscape)
    }
  }, [isOpen])

  // Fetch stats when opening
  useEffect(() => {
    if (isOpen) {
      fetchStats()
      // Auto-refresh every 2 seconds while open
      const interval = setInterval(fetchStats, 2000)
      return () => clearInterval(interval)
    }
  }, [isOpen])

  const fetchStats = async () => {
    setIsLoading(true)
    setError(null)
    try {
      // Use authFetch to include Authorization header
      const token = localStorage.getItem('auth_token')
      const response = await fetch('/api/v1/chat/performance/stats', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (!response.ok) {
        throw new Error('Failed to fetch stats')
      }
      const data = await response.json()
      setStats(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch stats')
    } finally {
      setIsLoading(false)
    }
  }

  const formatUptime = (seconds?: number) => {
    if (!seconds) return '0m'
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    if (hours > 0) {
      return `${hours}h ${minutes}m`
    }
    return `${minutes}m`
  }

  const getThermalColor = (state?: string) => {
    switch (state?.toLowerCase()) {
      case 'nominal':
        return 'text-green-500'
      case 'fair':
        return 'text-yellow-500'
      case 'serious':
        return 'text-orange-500'
      case 'critical':
        return 'text-red-500'
      default:
        return 'text-gray-400'
    }
  }

  return (
    <div className="relative">
      {/* Trigger Button */}
      <button
        onClick={handleToggle}
        className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors text-gray-600 dark:text-gray-400 hover:text-green-600 dark:hover:text-green-400"
        title="Performance Monitor"
      >
        <Activity size={20} />
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div
          className="absolute top-full right-0 mt-2 w-80 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg shadow-xl flex flex-col z-50"
          ref={dropdownRef}
        >
          {/* Header */}
          <div className="p-3 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
            <Activity className="w-4 h-4 text-green-500" />
            <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
              Performance Monitor
            </div>
          </div>

          {/* Stats Content */}
          <div className="p-4 space-y-4">
            {error ? (
              <div className="text-center py-8 text-sm text-red-500">
                {error}
              </div>
            ) : !stats ? (
              <div className="text-center py-8 text-sm text-gray-500 dark:text-gray-400">
                Loading...
              </div>
            ) : (
              <>
                {/* Current Stats */}
                <div>
                  <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                    Current
                  </div>
                  <div className="space-y-2">
                    {/* Tokens/sec */}
                    <div className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded">
                      <div className="flex items-center gap-2">
                        <Zap className="w-4 h-4 text-blue-500" />
                        <span className="text-sm text-gray-700 dark:text-gray-300">Tokens/sec</span>
                      </div>
                      <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                        {stats.current?.tokens_per_second?.toFixed(1) || 'N/A'}
                      </span>
                    </div>

                    {/* CPU */}
                    <div className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded">
                      <div className="flex items-center gap-2">
                        <Cpu className="w-4 h-4 text-purple-500" />
                        <span className="text-sm text-gray-700 dark:text-gray-300">CPU</span>
                      </div>
                      <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                        {stats.current?.cpu_percent?.toFixed(0) || '0'}%
                      </span>
                    </div>

                    {/* Memory */}
                    <div className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded">
                      <div className="flex items-center gap-2">
                        <TrendingUp className="w-4 h-4 text-orange-500" />
                        <span className="text-sm text-gray-700 dark:text-gray-300">Memory</span>
                      </div>
                      <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                        {stats.current?.memory_percent?.toFixed(0) || '0'}%
                      </span>
                    </div>

                    {/* Thermal */}
                    <div className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded">
                      <div className="flex items-center gap-2">
                        <Thermometer className="w-4 h-4 text-red-500" />
                        <span className="text-sm text-gray-700 dark:text-gray-300">Thermal</span>
                      </div>
                      <span className={`text-sm font-semibold capitalize ${getThermalColor(stats.current?.thermal_state)}`}>
                        {stats.current?.thermal_state || 'unknown'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Averages */}
                <div>
                  <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                    Averages
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded">
                      <span className="text-sm text-gray-700 dark:text-gray-300">Tokens/sec</span>
                      <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                        {stats.averages?.tokens_per_second?.toFixed(1) || 'N/A'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded">
                      <span className="text-sm text-gray-700 dark:text-gray-300">CPU</span>
                      <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                        {stats.averages?.cpu_percent?.toFixed(0) || '0'}%
                      </span>
                    </div>
                  </div>
                </div>

                {/* Uptime */}
                <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-500 dark:text-gray-400">Uptime</span>
                    <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                      {formatUptime(stats.uptime_seconds)}
                    </span>
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Footer */}
          <div className="p-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/50">
            <div className="text-xs text-center text-gray-500 dark:text-gray-400">
              Auto-refreshes every 2 seconds
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
