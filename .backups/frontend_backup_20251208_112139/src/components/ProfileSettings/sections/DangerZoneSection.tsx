/**
 * DangerZoneSection Component
 *
 * Destructive actions and account management
 */

import { User, RefreshCw, Trash2, AlertTriangle, Power, Database } from 'lucide-react'
import { useState, useEffect } from 'react'
import { SectionHeader } from '../components/SectionHeader'
import type { DangerHandlers, ServerControlHandlers, SystemRefreshHandlers } from '../types'

interface DangerZoneSectionProps {
  dangerHandlers: DangerHandlers
  serverControlHandlers: ServerControlHandlers
  systemRefreshHandlers: SystemRefreshHandlers
}

export function DangerZoneSection({ dangerHandlers, serverControlHandlers, systemRefreshHandlers }: DangerZoneSectionProps) {
  const [serverStatuses, setServerStatuses] = useState({
    ollama: 'unknown',
    backend: 'unknown',
    websocket: 'unknown'
  })

  useEffect(() => {
    // Fetch initial server statuses
    const fetchStatuses = async () => {
      try {
        const token = localStorage.getItem('auth_token')
        const response = await fetch('/api/v1/diagnostics', {
          headers: {
            'Authorization': token ? `Bearer ${token}` : '',
            'Content-Type': 'application/json'
          }
        })
        if (response.ok) {
          const data = await response.json()
          console.log('Diagnostics data:', data)
          setServerStatuses({
            ollama: data.ollama?.status || 'unknown',
            backend: 'running', // If we got a response, backend is running
            websocket: 'running' // TODO: Add actual WebSocket status check
          })
        } else {
          console.error('Failed to fetch diagnostics:', response.status, await response.text())
        }
      } catch (error) {
        console.error('Failed to fetch server statuses:', error)
      }
    }
    fetchStatuses()
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'text-green-500'
      case 'offline':
      case 'stopped':
        return 'text-red-500'
      default:
        return 'text-yellow-500'
    }
  }

  const getStatusDot = (status: string) => {
    const colorClass = getStatusColor(status)
    return <span className={`inline-block w-2 h-2 rounded-full ${colorClass.replace('text-', 'bg-')}`}></span>
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-red-600 dark:text-red-400 mb-1">
          Danger Zone
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Irreversible actions - proceed with caution
        </p>
      </div>

      <div className="space-y-3">
        {/* Server Controls Tile */}
        <div className="p-4 border-2 border-blue-200 dark:border-blue-900 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <div className="flex items-start gap-3 mb-3">
            <Power className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5" />
            <div className="flex-1">
              <div className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-1">
                Server Controls
              </div>
              <div className="text-xs text-blue-700 dark:text-blue-300 mb-4">
                Start, stop, or restart individual services
              </div>

              {/* Ollama Server */}
              <div className="space-y-2 mb-3">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    {getStatusDot(serverStatuses.ollama)}
                    <span className="text-gray-700 dark:text-gray-300">Ollama Server</span>
                  </div>
                  <span className={`font-medium ${getStatusColor(serverStatuses.ollama)}`}>
                    {serverStatuses.ollama}
                  </span>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={serverControlHandlers.handleStartOllama}
                    className="flex-1 px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded text-xs font-medium transition-colors"
                  >
                    Start
                  </button>
                  <button
                    onClick={serverControlHandlers.handleStopOllama}
                    className="flex-1 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded text-xs font-medium transition-colors"
                  >
                    Stop
                  </button>
                  <button
                    onClick={serverControlHandlers.handleRestartOllama}
                    className="flex-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-medium transition-colors"
                  >
                    Restart
                  </button>
                </div>
              </div>

              {/* Backend API */}
              <div className="space-y-2 mb-3">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    {getStatusDot(serverStatuses.backend)}
                    <span className="text-gray-700 dark:text-gray-300">Backend API</span>
                  </div>
                  <span className={`font-medium ${getStatusColor(serverStatuses.backend)}`}>
                    {serverStatuses.backend}
                  </span>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={serverControlHandlers.handleStartBackend}
                    className="flex-1 px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded text-xs font-medium transition-colors"
                  >
                    Start
                  </button>
                  <button
                    onClick={serverControlHandlers.handleStopBackend}
                    className="flex-1 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded text-xs font-medium transition-colors"
                  >
                    Stop
                  </button>
                  <button
                    onClick={serverControlHandlers.handleRestartBackend}
                    className="flex-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-medium transition-colors"
                  >
                    Restart
                  </button>
                </div>
              </div>

              {/* WebSocket */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    {getStatusDot(serverStatuses.websocket)}
                    <span className="text-gray-700 dark:text-gray-300">WebSocket</span>
                  </div>
                  <span className={`font-medium ${getStatusColor(serverStatuses.websocket)}`}>
                    {serverStatuses.websocket}
                  </span>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={serverControlHandlers.handleStartWebSocket}
                    className="flex-1 px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded text-xs font-medium transition-colors"
                  >
                    Start
                  </button>
                  <button
                    onClick={serverControlHandlers.handleStopWebSocket}
                    className="flex-1 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded text-xs font-medium transition-colors"
                  >
                    Stop
                  </button>
                  <button
                    onClick={serverControlHandlers.handleRestartWebSocket}
                    className="flex-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-medium transition-colors"
                  >
                    Restart
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* System Refresh Tile */}
        <div className="p-4 border-2 border-teal-200 dark:border-teal-900 bg-teal-50 dark:bg-teal-900/20 rounded-lg">
          <div className="flex items-start gap-3 mb-3">
            <Database className="w-5 h-5 text-teal-600 dark:text-teal-400 mt-0.5" />
            <div className="flex-1">
              <div className="text-sm font-semibold text-teal-900 dark:text-teal-100 mb-1">
                Refresh & Reload
              </div>
              <div className="text-xs text-teal-700 dark:text-teal-300 mb-4">
                Reset connections or reload data without full restart
              </div>

              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={systemRefreshHandlers.handleRefreshOllama}
                  className="px-3 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-xs font-medium transition-colors"
                >
                  Refresh Ollama
                </button>
                <button
                  onClick={systemRefreshHandlers.handleRefreshDatabases}
                  className="px-3 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-xs font-medium transition-colors"
                >
                  Refresh Databases
                </button>
                <button
                  onClick={systemRefreshHandlers.handleReloadBackend}
                  className="px-3 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-xs font-medium transition-colors"
                >
                  Reload Backend
                </button>
                <button
                  onClick={systemRefreshHandlers.handleClearCache}
                  className="px-3 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-xs font-medium transition-colors"
                >
                  Clear Cache
                </button>
              </div>
            </div>
          </div>
        </div>
        {/* Logout Button */}
        <div className="p-4 border-2 border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
          <div className="flex items-start gap-3 mb-3">
            <User className="w-5 h-5 text-gray-600 dark:text-gray-400 mt-0.5" />
            <div className="flex-1">
              <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-1">
                Logout
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400 mb-3">
                Sign out of your account and return to the login screen
              </div>
              <button
                onClick={dangerHandlers.handleLogout}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>

        {/* Reset User Identity */}
        <div className="p-4 border-2 border-orange-200 dark:border-orange-900 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
          <div className="flex items-start gap-3 mb-3">
            <RefreshCw className="w-5 h-5 text-orange-600 dark:text-orange-400 mt-0.5" />
            <div className="flex-1">
              <div className="text-sm font-semibold text-orange-900 dark:text-orange-100 mb-1">
                Reset User Identity
              </div>
              <div className="text-xs text-orange-700 dark:text-orange-300 mb-3">
                Generate new User ID. Your documents and data will be preserved.
              </div>
              <button
                onClick={dangerHandlers.handleResetIdentity}
                className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                Reset Identity
              </button>
            </div>
          </div>
        </div>

        {/* Delete All Data */}
        <div className="p-4 border-2 border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-900/20 rounded-lg">
          <div className="flex items-start gap-3 mb-3">
            <Trash2 className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5" />
            <div className="flex-1">
              <div className="text-sm font-semibold text-red-900 dark:text-red-100 mb-1">
                Delete All Local Data
              </div>
              <div className="text-xs text-red-700 dark:text-red-300 mb-3">
                Remove all documents, chats, and files. Settings will be preserved. Cannot
                be undone.
              </div>
              <button
                onClick={dangerHandlers.handleDeleteAllData}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                Delete All Data
              </button>
            </div>
          </div>
        </div>

        {/* Factory Reset */}
        <div className="p-4 border-2 border-red-300 dark:border-red-900 bg-red-100 dark:bg-red-950/40 rounded-lg">
          <div className="flex items-start gap-3 mb-3">
            <AlertTriangle className="w-5 h-5 text-red-700 dark:text-red-400 mt-0.5" />
            <div className="flex-1">
              <div className="text-sm font-semibold text-red-950 dark:text-red-50 mb-1">
                Factory Reset
              </div>
              <div className="text-xs text-red-800 dark:text-red-200 mb-3">
                Complete wipe - deletes everything (data + settings + identity). Like a
                fresh install. Cannot be undone.
              </div>
              <button
                onClick={dangerHandlers.handleFactoryReset}
                className="px-4 py-2 bg-red-700 hover:bg-red-800 text-white rounded-lg text-sm font-medium transition-colors"
              >
                Factory Reset
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
