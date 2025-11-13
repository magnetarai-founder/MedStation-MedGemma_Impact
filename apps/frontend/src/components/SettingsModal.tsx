import { useState, useEffect, lazy, Suspense } from 'react'
import { X, Settings as SettingsIcon, Zap, AlertTriangle, Cpu, User, Loader2, Shield, MessageSquare, Sparkles, Workflow, Crown, BarChart3 } from 'lucide-react'
import { type NavTab } from '@/stores/navigationStore'
import { usePermissions } from '@/hooks/usePermissions'
import { ProfileSettings } from './ProfileSettings'
import { ROLES } from '@/lib/roles'

// Lazy load heavy tab components for better performance
const ChatTab = lazy(() => import('./settings/ChatTab'))
const ModelsTab = lazy(() => import('./settings/ModelsTab'))
const PermissionsTab = lazy(() => import('./settings/PermissionsTab'))
const AppSettingsTab = lazy(() => import('./settings/AppSettingsTab'))
const AutomationTab = lazy(() => import('./settings/AutomationTab'))
const AdvancedTab = lazy(() => import('./settings/AdvancedTab'))
const SecurityTab = lazy(() => import('./settings/SecurityTab'))
const DangerZoneTab = lazy(() => import('./settings/DangerZoneTab'))
const AdminTab = lazy(() => import('./settings/AdminTab'))
const AnalyticsTab = lazy(() => import('./settings/AnalyticsTab'))


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
  const [activeTab, setActiveTab] = useState<'profile' | 'admin' | 'chat' | 'models' | 'permissions' | 'app' | 'automation' | 'advanced' | 'security' | 'danger' | 'analytics'>('profile')
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

            {/* Admin Dashboard - Founder Rights only */}
            {userRole === ROLES.GOD_RIGHTS && (
              <button
                onClick={() => setActiveTab('admin')}
                className={`w-full flex items-center gap-3 px-3 py-2 text-sm font-medium transition-all rounded-lg ${
                  activeTab === 'admin'
                    ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800/50'
                }`}
              >
                <Crown className="w-4 h-4" />
                <span>Admin</span>
              </button>
            )}

            {/* Analytics - Admin/Founder only (Sprint 6) */}
            {(userRole === ROLES.GOD_RIGHTS || userRole === 'admin') && (
              <button
                onClick={() => setActiveTab('analytics')}
                className={`w-full flex items-center gap-3 px-3 py-2 text-sm font-medium transition-all rounded-lg ${
                  activeTab === 'analytics'
                    ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800/50'
                }`}
              >
                <BarChart3 className="w-4 h-4" />
                <span>Analytics</span>
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
              onClick={() => setActiveTab('permissions')}
              className={`w-full flex items-center gap-3 px-3 py-2 text-sm font-medium transition-all rounded-lg ${
                activeTab === 'permissions'
                  ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800/50'
              }`}
            >
              <Shield className="w-4 h-4" />
              <span>Permissions</span>
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

            <button
              onClick={() => setActiveTab('security')}
              className={`w-full flex items-center gap-3 px-3 py-2 text-sm font-medium transition-all rounded-lg ${
                activeTab === 'security'
                  ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800/50'
              }`}
            >
              <Shield className="w-4 h-4" />
              <span>Security & Vault</span>
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
              <span>System Management</span>
            </button>
          </nav>
        </div>

        {/* Content Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Content Header */}
          <div className="flex items-center justify-between px-8 py-5 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              {activeTab === 'profile' && 'Profile'}
              {activeTab === 'admin' && 'Founder Rights Admin'}
              {activeTab === 'analytics' && 'Analytics Dashboard'}
              {activeTab === 'chat' && 'Chat'}
              {activeTab === 'models' && 'Models'}
              {activeTab === 'permissions' && 'Permissions'}
              {activeTab === 'app' && 'App'}
              {activeTab === 'automation' && 'Automation'}
              {activeTab === 'advanced' && 'Advanced'}
              {activeTab === 'security' && 'Security & Vault'}
              {activeTab === 'danger' && 'System Management'}
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
              {/* Always render ProfileSettings (not lazy loaded) */}
              <div className={activeTab === 'profile' ? '' : 'hidden'}>
                <ProfileSettings />
              </div>

              {/* Render active tab immediately */}
              {activeTab === 'admin' && (
                <div>
                  <AdminTab />
                </div>
              )}
              {activeTab === 'analytics' && (
                <div>
                  <AnalyticsTab />
                </div>
              )}
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
              {activeTab === 'permissions' && (
                <div>
                  <PermissionsTab />
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
              {activeTab === 'security' && (
                <div>
                  <SecurityTab />
                </div>
              )}
              {activeTab === 'danger' && (
                <div>
                  <DangerZoneTab />
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
                  {activeTab !== 'security' && (
                    <div className="hidden">
                      <SecurityTab />
                    </div>
                  )}
                  {activeTab !== 'danger' && (
                    <div className="hidden">
                      <DangerZoneTab />
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
