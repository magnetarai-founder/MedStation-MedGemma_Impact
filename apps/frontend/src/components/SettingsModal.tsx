import { useState, useEffect, lazy, Suspense } from 'react'
import { X, Settings as SettingsIcon, Zap, AlertTriangle, Cpu, User, Loader2, Plug, Shield, Database, FileText, Accessibility } from 'lucide-react'
import { type NavTab } from '@/stores/navigationStore'
import { ProfileSettings } from './ProfileSettings'

// Lazy load heavy tab components for better performance
const SettingsTab = lazy(() => import('./settings/SettingsTab'))
const SecurityTab = lazy(() => import('./settings/SecurityTab'))
const PowerUserTab = lazy(() => import('./settings/PowerUserTab'))
const ModelManagementTab = lazy(() => import('./settings/ModelManagementTab'))
const IntegrationsTab = lazy(() => import('./settings/IntegrationsTab'))
const DangerZoneTab = lazy(() => import('./settings/DangerZoneTab'))


interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
  activeNavTab: NavTab
}


// Loading fallback for lazy-loaded tabs
function LoadingFallback() {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="flex items-center gap-3 text-gray-500 dark:text-gray-400">
        <Loader2 className="w-5 h-5 animate-spin" />
        <span>Loading...</span>
      </div>
    </div>
  )
}

export function SettingsModal({ isOpen, onClose, activeNavTab }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<'profile' | 'settings' | 'security' | 'power' | 'models' | 'integrations' | 'danger'>('settings')

  // Handle ESC key to close modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
      />

      {/* Modal */}
      <div className="relative w-full max-w-4xl max-h-[85vh] bg-white dark:bg-gray-900 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <SettingsIcon className="w-6 h-6 text-primary-600 dark:text-primary-400" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              Global Settings
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 dark:border-gray-700 px-6">
          <button
            onClick={() => setActiveTab('profile')}
            className={`
              flex items-center space-x-2 px-4 py-3 border-b-2 transition-colors
              ${activeTab === 'profile'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }
            `}
          >
            <User className="w-4 h-4" />
            <span className="font-medium">Profile</span>
          </button>
          <button
            onClick={() => setActiveTab('settings')}
            className={`
              flex items-center space-x-2 px-4 py-3 border-b-2 transition-colors
              ${activeTab === 'settings'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }
            `}
          >
            <SettingsIcon className="w-4 h-4" />
            <span className="font-medium">App Settings</span>
          </button>
          <button
            onClick={() => setActiveTab('security')}
            className={`
              flex items-center space-x-2 px-4 py-3 border-b-2 transition-colors
              ${activeTab === 'security'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }
            `}
          >
            <Shield className="w-4 h-4" />
            <span className="font-medium">Security</span>
          </button>
          <button
            onClick={() => setActiveTab('power')}
            className={`
              flex items-center space-x-2 px-4 py-3 border-b-2 transition-colors
              ${activeTab === 'power'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }
            `}
          >
            <Zap className="w-4 h-4" />
            <span className="font-medium">Advanced</span>
          </button>
          <button
            onClick={() => setActiveTab('models')}
            className={`
              flex items-center space-x-2 px-4 py-3 border-b-2 transition-colors
              ${activeTab === 'models'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }
            `}
          >
            <Cpu className="w-4 h-4" />
            <span className="font-medium">Model Management</span>
          </button>
          <button
            onClick={() => setActiveTab('integrations')}
            className={`
              flex items-center space-x-2 px-4 py-3 border-b-2 transition-colors
              ${activeTab === 'integrations'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }
            `}
          >
            <Plug className="w-4 h-4" />
            <span className="font-medium">Integrations</span>
          </button>
          <button
            onClick={() => setActiveTab('danger')}
            className={`
              flex items-center space-x-2 px-4 py-3 border-b-2 transition-colors
              ${activeTab === 'danger'
                ? 'border-red-500 text-red-600 dark:text-red-400'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }
            `}
          >
            <AlertTriangle className="w-4 h-4" />
            <span className="font-medium">Danger Zone</span>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          <Suspense fallback={<LoadingFallback />}>
            {activeTab === 'profile' && <ProfileSettings />}
            {activeTab === 'settings' && <SettingsTab activeNavTab={activeNavTab} />}
            {activeTab === 'security' && <SecurityTab />}
            {activeTab === 'power' && <PowerUserTab />}
            {activeTab === 'models' && <ModelManagementTab />}
            {activeTab === 'integrations' && <IntegrationsTab />}
            {activeTab === 'danger' && <DangerZoneTab />}
          </Suspense>
        </div>
      </div>
    </div>
  )
}
