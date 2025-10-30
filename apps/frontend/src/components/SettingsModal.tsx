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
      <div className="relative w-full max-w-5xl max-h-[85vh] bg-white dark:bg-gray-900 rounded-2xl shadow-2xl flex overflow-hidden">
        {/* Sidebar */}
        <div className="w-56 bg-gray-50 dark:bg-gray-800/30 flex flex-col border-r border-gray-200 dark:border-gray-700">
          {/* Header */}
          <div className="flex items-center gap-3 px-5 py-5 h-[73px] border-b border-gray-200 dark:border-gray-700">
            <SettingsIcon className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Settings
            </h2>
          </div>

          {/* Navigation */}
          <nav className="flex-1 overflow-y-auto py-3 px-3 space-y-1">
            <button
              onClick={() => setActiveTab('profile')}
              className={`w-full flex items-center gap-3 px-3 py-2 text-sm font-medium transition-all rounded-lg ${
                activeTab === 'profile'
                  ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800/50'
              }`}
            >
              <User className="w-4 h-4" />
              <span>Profile</span>
            </button>

            <button
              onClick={() => setActiveTab('chat')}
              className={`w-full flex items-center gap-3 px-3 py-2 text-sm font-medium transition-all rounded-lg ${
                activeTab === 'chat'
                  ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800/50'
              }`}
            >
              <MessageSquare className="w-4 h-4" />
              <span>Chat</span>
            </button>

            <button
              onClick={() => setActiveTab('models')}
              className={`w-full flex items-center gap-3 px-3 py-2 text-sm font-medium transition-all rounded-lg ${
                activeTab === 'models'
                  ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800/50'
              }`}
            >
              <Sparkles className="w-4 h-4" />
              <span>Models</span>
            </button>

            <button
              onClick={() => setActiveTab('app')}
              className={`w-full flex items-center gap-3 px-3 py-2 text-sm font-medium transition-all rounded-lg ${
                activeTab === 'app'
                  ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800/50'
              }`}
            >
              <SettingsIcon className="w-4 h-4" />
              <span>App</span>
            </button>

            <button
              onClick={() => setActiveTab('automation')}
              className={`w-full flex items-center gap-3 px-3 py-2 text-sm font-medium transition-all rounded-lg ${
                activeTab === 'automation'
                  ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800/50'
              }`}
            >
              <Workflow className="w-4 h-4" />
              <span>Automation</span>
            </button>

            <button
              onClick={() => setActiveTab('advanced')}
              className={`w-full flex items-center gap-3 px-3 py-2 text-sm font-medium transition-all rounded-lg ${
                activeTab === 'advanced'
                  ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800/50'
              }`}
            >
              <Zap className="w-4 h-4" />
              <span>Advanced</span>
            </button>

            <button
              onClick={() => setActiveTab('security')}
              className={`w-full flex items-center gap-3 px-3 py-2 text-sm font-medium transition-all rounded-lg ${
                activeTab === 'security'
                  ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800/50'
              }`}
            >
              <Shield className="w-4 h-4" />
              <span>Security</span>
            </button>

            <button
              onClick={() => setActiveTab('danger')}
              className={`w-full flex items-center gap-3 px-3 py-2 text-sm font-medium transition-all rounded-lg ${
                activeTab === 'danger'
                  ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800/50'
              }`}
            >
              <AlertTriangle className="w-4 h-4" />
              <span>Danger Zone</span>
            </button>
          </nav>
        </div>

        {/* Content Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Content Header */}
          <div className="flex items-center justify-between px-8 py-5 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              {activeTab === 'profile' && 'Profile'}
              {activeTab === 'chat' && 'Chat'}
              {activeTab === 'models' && 'Models'}
              {activeTab === 'app' && 'App'}
              {activeTab === 'automation' && 'Automation'}
              {activeTab === 'advanced' && 'Advanced'}
              {activeTab === 'security' && 'Security'}
              {activeTab === 'danger' && 'Danger Zone'}
            </h3>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-auto p-8">
            <Suspense fallback={<LoadingFallback />}>
              <div className={activeTab === 'profile' ? '' : 'hidden'}>
                <ProfileSettings />
              </div>
              <div className={activeTab === 'chat' ? '' : 'hidden'}>
                <ChatTab />
              </div>
              <div className={activeTab === 'models' ? '' : 'hidden'}>
                <ModelsTab />
              </div>
              <div className={activeTab === 'app' ? '' : 'hidden'}>
                <AppSettingsTab activeNavTab={activeNavTab} />
              </div>
              <div className={activeTab === 'automation' ? '' : 'hidden'}>
                <AutomationTab />
              </div>
              <div className={activeTab === 'advanced' ? '' : 'hidden'}>
                <AdvancedTab />
              </div>
              <div className={activeTab === 'security' ? '' : 'hidden'}>
                <SecurityTab />
              </div>
              <div className={activeTab === 'danger' ? '' : 'hidden'}>
                <DangerZoneTab />
              </div>
            </Suspense>
          </div>
        </div>
      </div>
    </div>
  )
}
