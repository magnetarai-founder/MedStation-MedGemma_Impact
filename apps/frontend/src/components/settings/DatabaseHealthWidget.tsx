/**
 * Database Health Widget
 *
 * Displays database path and table counts for admin monitoring
 */

import { useState, useEffect } from 'react'
import { Database, HardDrive, RefreshCw, CheckCircle, AlertCircle } from 'lucide-react'
import { api } from '@/lib/api'

interface DBHealth {
  status: string
  database_path: string
  database_exists: boolean
  database_size_mb: number
  table_counts: Record<string, number>
}

export function DatabaseHealthWidget() {
  const [health, setHealth] = useState<DBHealth | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchHealth = async () => {
    try {
      setLoading(true)
      setError(null)
      // axios baseURL is '/api' so use '/v1/system/db-health'
      const response = await api.get('/v1/system/db-health')
      setHealth(response.data)
    } catch (err: any) {
      console.error('Failed to fetch DB health:', err)
      setError(err.message || 'Failed to load database health')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHealth()
  }, [])

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3">
          <Database className="w-5 h-5 text-gray-400 animate-pulse" />
          <h3 className="font-semibold text-gray-900 dark:text-gray-100">Database Health</h3>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">Loading...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-red-200 dark:border-red-700">
        <div className="flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-500" />
          <h3 className="font-semibold text-gray-900 dark:text-gray-100">Database Health</h3>
        </div>
        <p className="text-sm text-red-600 dark:text-red-400 mt-2">{error}</p>
        <button
          onClick={fetchHealth}
          className="mt-3 text-sm text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1"
        >
          <RefreshCw className="w-3 h-3" />
          Retry
        </button>
      </div>
    )
  }

  if (!health) return null

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Database className="w-5 h-5 text-green-500" />
          <h3 className="font-semibold text-gray-900 dark:text-gray-100">Database Health</h3>
        </div>
        <button
          onClick={fetchHealth}
          className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          title="Refresh"
        >
          <RefreshCw className="w-4 h-4 text-gray-500 dark:text-gray-400" />
        </button>
      </div>

      {/* Database Info */}
      <div className="space-y-3 mb-4">
        <div className="flex items-center gap-2">
          {health.database_exists ? (
            <CheckCircle className="w-4 h-4 text-green-500" />
          ) : (
            <AlertCircle className="w-4 h-4 text-red-500" />
          )}
          <span className="text-sm text-gray-600 dark:text-gray-400">
            Status: {health.status}
          </span>
        </div>

        <div className="flex items-start gap-2">
          <HardDrive className="w-4 h-4 text-gray-400 mt-0.5" />
          <div className="flex-1">
            <p className="text-xs text-gray-500 dark:text-gray-400">Path</p>
            <p className="text-xs font-mono text-gray-700 dark:text-gray-300 break-all">
              {health.database_path}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600 dark:text-gray-400">
            Size: <span className="font-medium text-gray-900 dark:text-gray-100">{health.database_size_mb} MB</span>
          </span>
        </div>
      </div>

      {/* Table Counts */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Table Counts</h4>

        {/* Core Tables */}
        <div className="mb-3">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Core</p>
          <div className="grid grid-cols-2 gap-2">
            {['users', 'teams', 'team_members', 'workflows'].map(table => (
              <div key={table} className="flex justify-between text-xs">
                <span className="text-gray-600 dark:text-gray-400">{table}</span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {health.table_counts[table] ?? 0}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Kanban Tables */}
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Kanban Workspace</p>
          <div className="grid grid-cols-2 gap-2">
            {['kanban_projects', 'kanban_boards', 'kanban_columns', 'kanban_tasks', 'kanban_comments', 'kanban_wiki'].map(table => {
              const shortName = table.replace('kanban_', '')
              return (
                <div key={table} className="flex justify-between text-xs">
                  <span className="text-gray-600 dark:text-gray-400">{shortName}</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">
                    {health.table_counts[table] ?? 0}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
