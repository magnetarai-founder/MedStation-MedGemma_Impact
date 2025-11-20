/**
 * ProfileSettings Component
 *
 * Global user profile and settings - integrated into SettingsModal
 * Includes: Identity, Security, Updates, Privacy, Danger Zone
 */

import { useState } from 'react'
import { User, Shield, Cloud, Eye, AlertTriangle } from 'lucide-react'
import { useUserStore } from '@/stores/userStore'
import { useDocsStore } from '@/stores/docsStore'
import { useOllamaStore } from '@/stores/ollamaStore'
import toast from 'react-hot-toast'

// Hooks
import { useProfileData } from './hooks/useProfileData'
import { useProfileForm } from './hooks/useProfileForm'
import { useBiometricSetup } from './hooks/useBiometricSetup'

// Sections
import { IdentitySection } from './sections/IdentitySection'
import { SecuritySection } from './sections/SecuritySection'
import { UpdatesSection } from './sections/UpdatesSection'
import { PrivacySection } from './sections/PrivacySection'
import { DangerZoneSection } from './sections/DangerZoneSection'

// Types
import type { ProfileTab, TabConfig } from './types'

export function ProfileSettings() {
  const [activeTab, setActiveTab] = useState<ProfileTab>('identity')

  // Data fetching
  const { user, isLoading, fetchUser } = useProfileData()

  // Store access
  const { resetUser } = useUserStore()
  const { securitySettings, updateSecuritySettings } = useDocsStore()

  // Form state
  const { formState, handlers: formHandlers } = useProfileForm(user)

  // Biometric setup
  const { biometricState, handlers: biometricHandlers } = useBiometricSetup(user?.user_id)

  // Privacy handlers
  const handleExportData = () => {
    toast('Export data - Coming soon')
  }

  const handleImportBackup = () => {
    toast('Import backup - Coming soon')
  }

  // Danger zone handlers
  const handleLogout = async () => {
    try {
      // Call backend logout endpoint to delete session
      const token = localStorage.getItem('auth_token')
      if (token) {
        try {
          await fetch('http://localhost:8000/api/v1/auth/logout', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          })
          // Ignore errors - we'll clear local storage anyway
        } catch (err) {
          console.log('Logout API call failed (expected if token expired):', err)
        }
      }
    } finally {
      // Always clear local storage and reload, even if API call fails
      localStorage.removeItem('auth_token')
      localStorage.removeItem('user')
      window.location.reload()
    }
  }

  const handleResetIdentity = async () => {
    if (confirm('Reset your user identity? This will generate a new User ID. Your data will be preserved.')) {
      try {
        await resetUser()
        toast.success('User identity reset')
      } catch (error) {
        toast.error('Failed to reset identity')
      }
    }
  }

  const handleDeleteAllData = () => {
    if (
      confirm(
        'Delete ALL local data? This will remove all documents, chats, and files. Settings will be preserved. This cannot be undone.'
      )
    ) {
      toast.error('Delete all data - Coming soon')
      // TODO: Implement data deletion
    }
  }

  const handleFactoryReset = () => {
    if (
      confirm(
        'FACTORY RESET? This will delete everything - all data, settings, and user identity. This cannot be undone.'
      )
    ) {
      toast.error('Factory reset - Coming soon')
      // TODO: Implement factory reset
    }
  }

  // Server control handlers
  const handleStartOllama = async () => {
    try {
      const response = await fetch('/api/v1/chat/ollama/server/restart', { method: 'POST' })
      if (response.ok) {
        toast.success('Ollama server started')
      } else {
        toast.error('Failed to start Ollama server')
      }
    } catch (error) {
      toast.error('Error starting Ollama server')
    }
  }

  const handleStopOllama = async () => {
    try {
      const response = await fetch('/api/v1/chat/ollama/server/shutdown', { method: 'POST' })
      if (response.ok) {
        toast.success('Ollama server stopped')
      } else {
        toast.error('Failed to stop Ollama server')
      }
    } catch (error) {
      toast.error('Error stopping Ollama server')
    }
  }

  const handleRestartOllama = async () => {
    try {
      const response = await fetch('/api/v1/chat/ollama/server/restart?reload_models=true', { method: 'POST' })
      if (response.ok) {
        toast.success('Ollama server restarted')
      } else {
        toast.error('Failed to restart Ollama server')
      }
    } catch (error) {
      toast.error('Error restarting Ollama server')
    }
  }

  const handleStartBackend = async () => {
    toast('Backend start - Not applicable (already running)')
  }

  const handleStopBackend = async () => {
    toast.error('Cannot stop backend from within the app')
  }

  const handleRestartBackend = async () => {
    toast('Backend restart - Requires external restart')
  }

  const handleStartWebSocket = async () => {
    toast('WebSocket start - Not yet implemented')
  }

  const handleStopWebSocket = async () => {
    toast('WebSocket stop - Not yet implemented')
  }

  const handleRestartWebSocket = async () => {
    toast('WebSocket restart - Not yet implemented')
  }

  // System refresh handlers
  const handleRefreshOllama = async () => {
    try {
      const { fetchServerStatus, fetchModels } = useOllamaStore.getState()
      await fetchServerStatus()
      await fetchModels()
      toast.success('Ollama refreshed - reconnected and reloaded models')
    } catch (error) {
      toast.error('Failed to refresh Ollama')
    }
  }

  const handleRefreshDatabases = async () => {
    toast('Database refresh - Coming soon')
    // TODO: Implement database reconnection
  }

  const handleReloadBackend = async () => {
    try {
      const response = await fetch('/api/v1/diagnostics')
      if (response.ok) {
        toast.success('Backend connection refreshed')
      } else {
        toast.error('Failed to refresh backend connection')
      }
    } catch (error) {
      toast.error('Failed to refresh backend connection')
    }
  }

  const handleClearCache = async () => {
    toast('Cache cleared - Coming soon')
    // TODO: Implement cache clearing (query cache, request dedup cache, etc.)
  }

  // Tab configuration
  const tabs: TabConfig[] = [
    { id: 'identity' as const, label: 'Identity', icon: User },
    { id: 'security' as const, label: 'Security', icon: Shield },
    { id: 'updates' as const, label: 'Updates', icon: Cloud },
    { id: 'privacy' as const, label: 'Privacy', icon: Eye },
    { id: 'danger' as const, label: 'Danger Zone', icon: AlertTriangle },
  ]

  // Show loading only if actively loading AND no user data
  if (isLoading && !user) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading profile...</p>
        </div>
      </div>
    )
  }

  // If no user after loading, try to fetch and show error
  if (!user) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">Failed to load user profile</p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">Make sure the backend server is running</p>
          <button
            onClick={async () => {
              const { fetchUser } = useUserStore.getState()
              await fetchUser()
            }}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="flex gap-2 flex-wrap">
        {tabs.map((tab) => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 shadow-sm'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          )
        })}
      </div>

      {/* Tab Content */}
      <div className="bg-white dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        {activeTab === 'identity' && (
          <IdentitySection
            user={user}
            formState={formState}
            handlers={formHandlers}
          />
        )}

        {activeTab === 'security' && (
          <SecuritySection
            securitySettings={securitySettings}
            updateSecuritySettings={updateSecuritySettings}
            biometricState={biometricState}
            biometricHandlers={biometricHandlers}
          />
        )}

        {activeTab === 'updates' && <UpdatesSection />}

        {activeTab === 'privacy' && (
          <PrivacySection
            securitySettings={securitySettings}
            updateSecuritySettings={updateSecuritySettings}
            privacyHandlers={{
              handleExportData,
              handleImportBackup,
            }}
          />
        )}

        {activeTab === 'danger' && (
          <DangerZoneSection
            dangerHandlers={{
              handleLogout,
              handleResetIdentity,
              handleDeleteAllData,
              handleFactoryReset,
            }}
            serverControlHandlers={{
              handleStartOllama,
              handleStopOllama,
              handleRestartOllama,
              handleStartBackend,
              handleStopBackend,
              handleRestartBackend,
              handleStartWebSocket,
              handleStopWebSocket,
              handleRestartWebSocket,
            }}
            systemRefreshHandlers={{
              handleRefreshOllama,
              handleRefreshDatabases,
              handleReloadBackend,
              handleClearCache,
            }}
          />
        )}
      </div>
    </div>
  )
}
