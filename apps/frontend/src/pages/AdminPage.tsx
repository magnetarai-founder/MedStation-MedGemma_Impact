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
    <div className="h-full w-full flex flex-col">
      {/* Top Navigation Bar */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/30">
        <div className="flex items-center gap-1">
          {visibleTabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-md transition-all ${
                  activeTab === tab.id
                    ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 font-medium'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700/50'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Content Area - Direct render like TeamWorkspace */}
      <Suspense fallback={<LoadingFallback />}>
        {activeTab === 'system' && (
          <div className="flex-1 overflow-auto bg-gray-50 dark:bg-gray-900 p-6">
            <div className="flex items-center gap-3 mb-6">
              <Shield className="w-7 h-7 text-primary-500" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">System Diagnostics</h1>
                <p className="text-sm text-gray-600 dark:text-gray-400">Founder Rights admin dashboard with system-wide monitoring</p>
              </div>
            </div>
            {userRole === ROLES.GOD_RIGHTS && <AdminTab />}
            {userRole !== ROLES.GOD_RIGHTS && (
              <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
                <div className="flex items-center gap-3 text-amber-600 dark:text-amber-500 mb-4">
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
          <div className="flex-1 overflow-auto bg-gray-50 dark:bg-gray-900 p-6">
            <div className="flex items-center gap-3 mb-6">
              <Lock className="w-7 h-7 text-primary-500" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Security & Vault</h1>
                <p className="text-sm text-gray-600 dark:text-gray-400">Manage vault access, encryption, and security settings</p>
              </div>
            </div>
            <SecurityTab />
          </div>
        )}

        {activeTab === 'permissions' && (
          <div className="flex-1 overflow-auto bg-gray-50 dark:bg-gray-900 p-6">
            <div className="flex items-center gap-3 mb-6">
              <Users className="w-7 h-7 text-primary-500" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Teams & Permissions</h1>
                <p className="text-sm text-gray-600 dark:text-gray-400">Manage user roles, teams, and access controls</p>
              </div>
            </div>
            <PermissionsTab />
          </div>
        )}

        {activeTab === 'backups' && (
          <div className="flex-1 overflow-auto bg-gray-50 dark:bg-gray-900 p-6">
            <div className="flex items-center gap-3 mb-6">
              <Archive className="w-7 h-7 text-primary-500" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Backups & System Management</h1>
                <p className="text-sm text-gray-600 dark:text-gray-400">Configure automated backups and system maintenance</p>
              </div>
            </div>
            <BackupsTab />
            <div className="mt-8">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                Danger Zone
              </h3>
              <DangerZoneTab />
            </div>
          </div>
        )}

        {activeTab === 'profile' && (
          <div className="flex-1 overflow-auto bg-gray-50 dark:bg-gray-900 p-6">
            <div className="flex items-center gap-3 mb-6">
              <Activity className="w-7 h-7 text-primary-500" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Profile Settings</h1>
                <p className="text-sm text-gray-600 dark:text-gray-400">Manage your account preferences and settings</p>
              </div>
            </div>
            <ProfileSettings />
          </div>
        )}

        {activeTab === 'analytics' && (userRole === ROLES.GOD_RIGHTS || userRole === 'admin') && (
          <div className="flex-1 overflow-auto bg-gray-50 dark:bg-gray-900 p-6">
            <div className="flex items-center gap-3 mb-6">
              <BarChart3 className="w-7 h-7 text-primary-500" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Analytics Dashboard</h1>
                <p className="text-sm text-gray-600 dark:text-gray-400">System usage metrics and performance analytics</p>
              </div>
            </div>
            <AnalyticsTab />
          </div>
        )}
      </Suspense>
    </div>
  )
}
