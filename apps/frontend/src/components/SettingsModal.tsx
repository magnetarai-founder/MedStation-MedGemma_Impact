import { useState, useEffect, lazy, Suspense } from 'react'
import { X, Settings as SettingsIcon, Zap, AlertTriangle, Cpu, User, Loader2, Shield, MessageSquare, Sparkles } from 'lucide-react'
import { type NavTab } from '@/stores/navigationStore'
import { ProfileSettings } from './ProfileSettings'

// Lazy load heavy tab components for better performance
const ChatTab = lazy(() => import('./settings/ChatTab'))
const ModelsTab = lazy(() => import('./settings/ModelsTab'))
const AppSettingsTab = lazy(() => import('./settings/AppSettingsTab'))
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
  const [activeTab, setActiveTab] = useState<'profile' | 'chat' | 'models' | 'app' | 'advanced' | 'security' | 'danger'>('app')

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
        <div className="flex gap-2 border-b border-gray-200 dark:border-gray-700 px-6 py-2 overflow-x-auto scrollbar-hide">
          <button
            onClick={() => setActiveTab('profile')}
            className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-all whitespace-nowrap ${
              activeTab === 'profile'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400 font-semibold'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-md'
            }`}
          >
            <User className="w-4 h-4" />
            <span>Profile</span>
          </button>

          <button
            onClick={() => setActiveTab('chat')}
            className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-all whitespace-nowrap ${
              activeTab === 'chat'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400 font-semibold'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-md'
            }`}
          >
            <MessageSquare className="w-4 h-4" />
            <span>Chat</span>
          </button>

          <button
            onClick={() => setActiveTab('models')}
            className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-all whitespace-nowrap ${
              activeTab === 'models'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400 font-semibold'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-md'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            <span>Models</span>
          </button>

          <button
            onClick={() => setActiveTab('app')}
            className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-all whitespace-nowrap ${
              activeTab === 'app'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400 font-semibold'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-md'
            }`}
          >
            <SettingsIcon className="w-4 h-4" />
            <span>App</span>
          </button>

          <button
            onClick={() => setActiveTab('advanced')}
            className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-all whitespace-nowrap ${
              activeTab === 'advanced'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400 font-semibold'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-md'
            }`}
          >
            <Zap className="w-4 h-4" />
            <span>Advanced</span>
          </button>

          <button
            onClick={() => setActiveTab('security')}
            className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-all whitespace-nowrap ${
              activeTab === 'security'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400 font-semibold'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-md'
            }`}
          >
            <Shield className="w-4 h-4" />
            <span>Security</span>
          </button>

          <button
            onClick={() => setActiveTab('danger')}
            className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-all whitespace-nowrap ${
              activeTab === 'danger'
                ? 'border-red-500 text-red-600 dark:text-red-400 font-semibold'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-t-md'
            }`}
          >
            <AlertTriangle className="w-4 h-4" />
            <span>Danger Zone</span>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          <Suspense fallback={<LoadingFallback />}>
            {activeTab === 'profile' && <ProfileSettings />}
            {activeTab === 'chat' && <ChatTab />}
            {activeTab === 'models' && <ModelsTab />}
            {activeTab === 'app' && <AppSettingsTab activeNavTab={activeNavTab} />}
            {activeTab === 'advanced' && <AdvancedTab />}
            {activeTab === 'security' && <SecurityTab />}
            {activeTab === 'danger' && <DangerZoneTab />}
          </Suspense>
        </div>
      </div>
    </div>
  )
}
