import { useState, useEffect, lazy, Suspense } from 'react'
import { X, Settings as SettingsIcon, Zap, AlertTriangle, Cpu, User, Loader2, Shield, MessageSquare, Sparkles, Workflow, Crown, BarChart3, ArrowRight } from 'lucide-react'
import { type NavTab } from '@/stores/navigationStore'
import { usePermissions } from '@/hooks/usePermissions'
import { ProfileSettings } from './ProfileSettings/index'
import { ROLES } from '@/lib/roles'
import { useNavigationStore } from '@/stores/navigationStore'

// Lazy load heavy tab components for better performance
const ChatTab = lazy(() => import('./settings/ChatTab'))
const ModelsTab = lazy(() => import('./settings/ModelsTab'))
const AppSettingsTab = lazy(() => import('./settings/AppSettingsTab'))
const AutomationTab = lazy(() => import('./settings/AutomationTab'))
const AdvancedTab = lazy(() => import('./settings/AdvancedTab'))


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
  const permissions = usePermissions()
  const { setActiveTab: setNavTab } = useNavigationStore()
  const [activeTab, setActiveTab] = useState<'profile' | 'chat' | 'models' | 'app' | 'automation' | 'advanced'>('profile')
  const [preloaded, setPreloaded] = useState(false)
  const [userRole, setUserRole] = useState<string | null>(null)

  // Fetch user role on mount
  useEffect(() => {
    const fetchUserRole = async () => {
      try {
        const token = localStorage.getItem('auth_token')
        const response = await fetch('/api/v1/auth/me', {
          headers: {
            'Authorization': token ? `Bearer ${token}` : '',
            'Content-Type': 'application/json'
          }
        })
        if (response.ok) {
          const user = await response.json()
          console.log('SettingsModal - fetched user:', user)
          console.log('SettingsModal - user role:', user.role)
          setUserRole(user.role)
        } else {
          console.error('SettingsModal - failed to fetch user:', response.status)
        }
      } catch (error) {
        console.error('Failed to fetch user role:', error)
      }
    }

    if (isOpen) {
      fetchUserRole()
    }
  }, [isOpen])

  // Preload all tabs when modal opens to avoid jerkiness
  useEffect(() => {
    if (isOpen && !preloaded) {
      // Trigger lazy loading of all tabs by rendering them hidden
      setPreloaded(true)
    }
  }, [isOpen, preloaded])

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
      <div className="relative w-full max-w-5xl h-[85vh] bg-white dark:bg-gray-900 rounded-2xl shadow-2xl flex overflow-hidden">
        {/* Sidebar */}
        <div className="w-56 bg-gray-50 dark:bg-gray-800/30 flex flex-col border-r border-gray-200 dark:border-gray-700">
          {/* Header */}
          <div className="flex items-center gap-3 px-5 py-5 h-[73px]">
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

            {/* Link to Admin Page - Founder/Admin only */}
            {(userRole === ROLES.GOD_RIGHTS || userRole === 'admin') && (
              <button
                onClick={() => {
                  setNavTab('admin')
                  onClose()
                }}
                className="w-full flex items-center gap-3 px-3 py-2 text-sm font-medium transition-all rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800/50 border border-dashed border-gray-300 dark:border-gray-600"
              >
                <Shield className="w-4 h-4" />
                <span>Open Admin Page</span>
                <ArrowRight className="w-4 h-4 ml-auto" />
              </button>
            )}

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

            {/* Automation - Members and above only */}
            {permissions.canAccessAutomation && (
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
            )}

            {/* Advanced - Members and above only */}
            {permissions.canAccessAutomation && (
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
            )}

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
            </h3>            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-auto p-8">
            <Suspense fallback={<LoadingFallback />}>
              {/* Always render ProfileSettings (not lazy loaded) */}
              <div className={activeTab === 'profile' ? '' : 'hidden'}>
                <ProfileSettings />
              </div>

              {/* Render active tab immediately */}
              {activeTab === 'chat' && (
                <div>
                  <ChatTab />
                </div>
              )}
              {activeTab === 'models' && (
                <div>
                  <ModelsTab />
                </div>
              )}
              {activeTab === 'app' && (
                <div>
                  <AppSettingsTab activeNavTab={activeNavTab} />
                </div>
              )}
              {activeTab === 'automation' && (
                <div>
                  <AutomationTab />
                </div>
              )}
              {activeTab === 'advanced' && (
                <div>
                  <AdvancedTab />
                </div>
              )}
              {/* Preload all other tabs in hidden state after first render */}
              {preloaded && (
                <>
                  {activeTab !== 'chat' && (
                    <div className="hidden">
                      <ChatTab />
                    </div>
                  )}
                  {activeTab !== 'models' && (
                    <div className="hidden">
                      <ModelsTab />
                    </div>
                  )}
                  {activeTab !== 'app' && (
                    <div className="hidden">
                      <AppSettingsTab activeNavTab={activeNavTab} />
                    </div>
                  )}
                  {activeTab !== 'automation' && (
                    <div className="hidden">
                      <AutomationTab />
                    </div>
                  )}
                  {activeTab !== 'advanced' && (
                    <div className="hidden">
                      <AdvancedTab />
                    </div>
                  )}
                </>
              )}
            </Suspense>
          </div>
        </div>
      </div>
    </div>
  )
}
