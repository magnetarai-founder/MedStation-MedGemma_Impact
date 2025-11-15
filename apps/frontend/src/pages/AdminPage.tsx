import { useState, lazy, Suspense, useEffect } from 'react'
import { Shield, Server, Users, Archive, Loader2, Activity, Lock, AlertTriangle, BarChart3 } from 'lucide-react'
import { usePermissions } from '@/hooks/usePermissions'
import { ProfileSettings } from '../components/ProfileSettings/index'
import { ROLES } from '@/lib/roles'

// Lazy load tab components
const AdminTab = lazy(() => import('../components/settings/AdminTab'))
const SecurityTab = lazy(() => import('../components/settings/SecurityTab'))
const PermissionsTab = lazy(() => import('../components/settings/PermissionsTab'))
const DangerZoneTab = lazy(() => import('../components/settings/DangerZoneTab'))
const BackupsTab = lazy(() => import('../components/settings/BackupsTab'))
const AnalyticsTab = lazy(() => import('../components/settings/AnalyticsTab'))

// Loading fallback
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

type AdminTab = 'system' | 'security' | 'permissions' | 'backups' | 'profile' | 'analytics'

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<AdminTab>('system')
  const permissions = usePermissions()
  const [userRole, setUserRole] = useState<string | null>(null)

  // Fetch user role
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
          setUserRole(user.role)
        }
      } catch (error) {
        console.error('Failed to fetch user role:', error)
      }
    }
    fetchUserRole()
  }, [])

  const tabs = [
    { id: 'system' as AdminTab, label: 'System', icon: Server, visible: true },
    { id: 'security' as AdminTab, label: 'Security & Vault', icon: Lock, visible: true },
    { id: 'permissions' as AdminTab, label: 'Teams & Permissions', icon: Users, visible: true },
    { id: 'backups' as AdminTab, label: 'Backups & Logs', icon: Archive, visible: true },
    { id: 'profile' as AdminTab, label: 'Profile', icon: Activity, visible: true },
    { id: 'analytics' as AdminTab, label: 'Analytics', icon: BarChart3, visible: userRole === ROLES.GOD_RIGHTS || userRole === 'admin' },
  ]

  const visibleTabs = tabs.filter(tab => tab.visible)

  return (
    <div className="h-full flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-8 py-6">
        <div className="flex items-center gap-3 mb-2">
          <Shield className="w-6 h-6 text-primary-600 dark:text-primary-400" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Admin</h1>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Manage system settings, security, teams, and backups
        </p>
      </div>

      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* Sidebar */}
        <div className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 overflow-y-auto">
          <nav className="py-4 px-3 space-y-1">
            {visibleTabs.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium transition-all rounded-lg ${
                    activeTab === tab.id
                      ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50'
                  }`}
                  aria-current={activeTab === tab.id ? 'page' : undefined}
                >
                  <Icon className="w-4 h-4" />
                  <span>{tab.label}</span>
                </button>
              )
            })}
          </nav>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-auto bg-gray-50 dark:bg-gray-900">
          <div className="max-w-5xl mx-auto p-8">
            <Suspense fallback={<LoadingFallback />}>
              {activeTab === 'system' && (
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
                    System Diagnostics
                  </h2>
                  {userRole === ROLES.GOD_RIGHTS && <AdminTab />}
                  {userRole !== ROLES.GOD_RIGHTS && (
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
                      <div className="flex items-center gap-3 text-amber-600 dark:text-amber-400 mb-4">
                        <AlertTriangle className="w-5 h-5" />
                        <p className="font-medium">Founder Rights Required</p>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        System diagnostics and admin controls are only available to users with Founder Rights.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'security' && (
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
                    Security & Vault
                  </h2>
                  <SecurityTab />
                </div>
              )}

              {activeTab === 'permissions' && (
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
                    Teams & Permissions
                  </h2>
                  <PermissionsTab />
                </div>
              )}

              {activeTab === 'backups' && (
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
                    Backups & System Management
                  </h2>
                  <BackupsTab />
                  <div className="mt-8">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                      System Management
                    </h3>
                    <DangerZoneTab />
                  </div>
                </div>
              )}

              {activeTab === 'profile' && (
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
                    Profile Settings
                  </h2>
                  <ProfileSettings />
                </div>
              )}

              {activeTab === 'analytics' && (userRole === ROLES.GOD_RIGHTS || userRole === 'admin') && (
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
                    Analytics Dashboard
                  </h2>
                  <AnalyticsTab />
                </div>
              )}
            </Suspense>
          </div>
        </div>
      </div>
    </div>
  )
}
