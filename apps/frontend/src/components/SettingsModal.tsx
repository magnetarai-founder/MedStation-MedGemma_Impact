import { useState, useEffect, lazy, Suspense } from 'react'
import { X, Settings as SettingsIcon, Zap, AlertTriangle, Cpu, User, Loader2, Shield, MessageSquare, Sparkles, Workflow } from 'lucide-react'
import { type NavTab } from '@/stores/navigationStore'
import { ProfileSettings } from './ProfileSettings'

// Lazy load heavy tab components for better performance
const ChatTab = lazy(() => import('./settings/ChatTab'))
const ModelsTab = lazy(() => import('./settings/ModelsTab'))
const AppSettingsTab = lazy(() => import('./settings/AppSettingsTab'))
const AutomationTab = lazy(() => import('./settings/AutomationTab'))
const AdvancedTab = lazy(() => import('./settings/AdvancedTab'))
const SecurityTab = lazy(() => import('./settings/SecurityTab'))
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
  const [activeTab, setActiveTab] = useState<'profile' | 'chat' | 'models' | 'app' | 'automation' | 'advanced' | 'security' | 'danger'>('app')

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
              Settings
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
        <div className="flex gap-1 border-b border-gray-200 dark:border-gray-700 px-6 overflow-x-auto scrollbar-hide">
          <button
            onClick={() => setActiveTab('profile')}
            className={`flex items-center gap-2 px-3 py-2.5 text-sm font-medium transition-all whitespace-nowrap relative ${
              activeTab === 'profile'
                ? 'text-primary-600 dark:text-primary-400'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-lg'
            }`}
          >
            <User className="w-4 h-4" />
            <span>Profile</span>
            {activeTab === 'profile' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary-600 dark:bg-primary-400" />
            )}
          </button>

          <button
            onClick={() => setActiveTab('chat')}
            className={`flex items-center gap-2 px-3 py-2.5 text-sm font-medium transition-all whitespace-nowrap relative ${
              activeTab === 'chat'
                ? 'text-primary-600 dark:text-primary-400'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-lg'
            }`}
          >
            <MessageSquare className="w-4 h-4" />
            <span>Chat</span>
            {activeTab === 'chat' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary-600 dark:bg-primary-400" />
            )}
          </button>

          <button
            onClick={() => setActiveTab('models')}
            className={`flex items-center gap-2 px-3 py-2.5 text-sm font-medium transition-all whitespace-nowrap relative ${
              activeTab === 'models'
                ? 'text-primary-600 dark:text-primary-400'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-lg'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            <span>Models</span>
            {activeTab === 'models' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary-600 dark:bg-primary-400" />
            )}
          </button>

          <button
            onClick={() => setActiveTab('app')}
            className={`flex items-center gap-2 px-3 py-2.5 text-sm font-medium transition-all whitespace-nowrap relative ${
              activeTab === 'app'
                ? 'text-primary-600 dark:text-primary-400'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-lg'
            }`}
          >
            <SettingsIcon className="w-4 h-4" />
            <span>App</span>
            {activeTab === 'app' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary-600 dark:bg-primary-400" />
            )}
          </button>

          <button
            onClick={() => setActiveTab('automation')}
            className={`flex items-center gap-2 px-3 py-2.5 text-sm font-medium transition-all whitespace-nowrap relative ${
              activeTab === 'automation'
                ? 'text-primary-600 dark:text-primary-400'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-lg'
            }`}
          >
            <Workflow className="w-4 h-4" />
            <span>Automation</span>
            {activeTab === 'automation' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary-600 dark:bg-primary-400" />
            )}
          </button>

          <button
            onClick={() => setActiveTab('advanced')}
            className={`flex items-center gap-2 px-3 py-2.5 text-sm font-medium transition-all whitespace-nowrap relative ${
              activeTab === 'advanced'
                ? 'text-primary-600 dark:text-primary-400'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-lg'
            }`}
          >
            <Zap className="w-4 h-4" />
            <span>Advanced</span>
            {activeTab === 'advanced' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary-600 dark:bg-primary-400" />
            )}
          </button>

          <button
            onClick={() => setActiveTab('security')}
            className={`flex items-center gap-2 px-3 py-2.5 text-sm font-medium transition-all whitespace-nowrap relative ${
              activeTab === 'security'
                ? 'text-primary-600 dark:text-primary-400'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-lg'
            }`}
          >
            <Shield className="w-4 h-4" />
            <span>Security</span>
            {activeTab === 'security' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary-600 dark:bg-primary-400" />
            )}
          </button>

          <button
            onClick={() => setActiveTab('danger')}
            className={`flex items-center gap-2 px-3 py-2.5 text-sm font-medium transition-all whitespace-nowrap relative ${
              activeTab === 'danger'
                ? 'text-red-600 dark:text-red-400'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-lg'
            }`}
          >
            <AlertTriangle className="w-4 h-4" />
            <span>Danger Zone</span>
            {activeTab === 'danger' && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-red-600 dark:bg-red-400" />
            )}
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          <Suspense fallback={<LoadingFallback />}>
            {activeTab === 'profile' && <ProfileSettings />}
            {activeTab === 'chat' && <ChatTab />}
            {activeTab === 'models' && <ModelsTab />}
            {activeTab === 'app' && <AppSettingsTab activeNavTab={activeNavTab} />}
            {activeTab === 'automation' && <AutomationTab />}
            {activeTab === 'advanced' && <AdvancedTab />}
            {activeTab === 'security' && <SecurityTab />}
            {activeTab === 'danger' && <DangerZoneTab />}
          </Suspense>
        </div>
      </div>
    </div>
  )
}
