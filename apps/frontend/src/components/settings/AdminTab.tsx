/**
 * Founder Rights Admin Dashboard
 *
 * Founder admin panel for system-wide monitoring and user support
 * Only accessible to users with founder_rights role
 */

import { useState, useEffect } from 'react'
import { Shield, Users, MessageSquare, Workflow, Activity, TrendingUp, AlertCircle, Eye, ChevronRight, Heart, FileText, Key } from 'lucide-react'
import { ROLES } from '@/lib/roles'
import SystemHealthDashboard from '../SystemHealthDashboard'
import AuditLogViewer from '../AuditLogViewer'
import FounderSetupWizard from '../FounderSetupWizard'

interface DeviceOverview {
  total_users: number
  active_users_7d: number
  users_by_role: Record<string, number>
  total_chat_sessions: number | null
  total_workflows: number | null
  total_work_items: number | null
  total_documents: number | null
}

interface User {
  user_id: string
  username: string
  device_id: string
  created_at: string
  last_login: string | null
  is_active: boolean
  role: string
}

interface ChatSession {
  id: string
  title: string
  message_count: number
  created_at: string
  updated_at: string
}

export default function AdminTab() {
  const [activeView, setActiveView] = useState<'overview' | 'users' | 'user-detail' | 'health' | 'audit-logs' | 'founder-setup'>('overview')
  const [deviceOverview, setDeviceOverview] = useState<DeviceOverview | null>(null)
  const [users, setUsers] = useState<User[]>([])
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [userChats, setUserChats] = useState<ChatSession[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch device overview on mount
  useEffect(() => {
    fetchDeviceOverview()
  }, [])

  const fetchDeviceOverview = async () => {
    setLoading(true)
    setError(null)
    try {
      const token = localStorage.getItem('auth_token')
      const baseHeaders: Record<string,string> = { 'Content-Type': 'application/json' }
      if (token) baseHeaders['Authorization'] = `Bearer ${token}`

      const response = await fetch('/api/v1/admin/device/overview', {
        headers: baseHeaders
      })

      if (!response.ok) {
        if (response.status === 403) {
          throw new Error('Access Denied: Founder Rights (Founder Admin) role required')
        }
        if (response.status === 429) {
          throw new Error('Too many requests. Please wait a moment and try again.')
        }
        throw new Error(`Failed to fetch device overview: ${response.statusText}`)
      }

      const data = await response.json()
      setDeviceOverview(data.device_overview)
    } catch (err: any) {
      setError(err.message)
      console.error('Failed to fetch device overview:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchUsers = async () => {
    setLoading(true)
    setError(null)
    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch('/api/v1/admin/users', {
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch users: ${response.statusText}`)
      }

      const data = await response.json()
      setUsers(data.users)
      setActiveView('users')
    } catch (err: any) {
      setError(err.message)
      console.error('Failed to fetch users:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchUserDetails = async (user: User) => {
    setLoading(true)
    setError(null)
    setSelectedUser(user)

    try {
      const token = localStorage.getItem('auth_token')

      // Fetch user's chats
      const chatsResponse = await fetch(`/api/v1/admin/users/${user.user_id}/chats`, {
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
          'Content-Type': 'application/json'
        }
      })

      if (!chatsResponse.ok) {
        throw new Error(`Failed to fetch user chats: ${chatsResponse.statusText}`)
      }

      const chatsData = await chatsResponse.json()
      setUserChats(chatsData.sessions)
      setActiveView('user-detail')
    } catch (err: any) {
      setError(err.message)
      console.error('Failed to fetch user details:', err)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
  }

  const getRoleBadgeClass = (role: string) => {
    switch (role) {
      case ROLES.GOD_RIGHTS:
        return 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-700'
      case ROLES.ADMIN:
        return 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 border-orange-200 dark:border-orange-700'
      case ROLES.MEMBER:
        return 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-700'
      default:
        return 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-600'
    }
  }

  // Access Denied - Not Founder Rights
  if (error && error.includes('Access Denied')) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <Shield className="w-16 h-16 text-red-500 mb-4" />
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Access Denied
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 max-w-md">
          This admin dashboard is only accessible to users with Founder Rights (Founder Admin) role.
        </p>
      </div>
    )
  }

  // Overview View
  if (activeView === 'overview') {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start gap-3 p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
          <Shield className="w-5 h-5 text-purple-600 dark:text-purple-400 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-purple-900 dark:text-purple-100 mb-1">
              Founder Rights Admin Dashboard
            </h4>
            <p className="text-sm text-purple-700 dark:text-purple-300">
              System-wide monitoring and user support tools. All actions are audit logged.
            </p>
          </div>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
          </div>
        )}

        {/* Error State */}
        {error && !error.includes('Access Denied') && (
          <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="font-semibold text-red-900 dark:text-red-100 mb-1">Error</h4>
                <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Device Overview Stats */}
        {deviceOverview && (
          <>
            <div className="grid grid-cols-2 gap-4">
              {/* Total Users */}
              <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between mb-2">
                  <Users className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                  <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                    {deviceOverview.total_users}
                  </span>
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Total Users</div>
              </div>

              {/* Active Users */}
              <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between mb-2">
                  <Activity className="w-5 h-5 text-green-600 dark:text-green-400" />
                  <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                    {deviceOverview.active_users_7d}
                  </span>
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Active (7 days)</div>
              </div>

              {/* Chat Sessions */}
              <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between mb-2">
                  <MessageSquare className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                  <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                    {deviceOverview.total_chat_sessions ?? 'N/A'}
                  </span>
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Chat Sessions</div>
              </div>

              {/* Workflows */}
              <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between mb-2">
                  <Workflow className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                  <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                    {deviceOverview.total_workflows ?? 'N/A'}
                  </span>
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Workflows</div>
              </div>
            </div>

            {/* Users by Role */}
            <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
              <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">Users by Role</h4>
              <div className="space-y-2">
                {Object.entries(deviceOverview.users_by_role || {}).map(([role, count]) => (
                  <div key={role} className="flex items-center justify-between">
                    <span className={`px-2 py-1 text-xs font-medium rounded border ${getRoleBadgeClass(role)}`}>
                      {role || 'member'}
                    </span>
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{count}</span>
                  </div>
                ))}
                {!deviceOverview.users_by_role && (
                  <div className="text-sm text-gray-500 dark:text-gray-400">No role data available</div>
                )}
              </div>
            </div>
          </>
        )}

        {/* Quick Actions */}
        <div className="grid grid-cols-1 gap-3">
          <button
            onClick={fetchUsers}
            className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-purple-300 dark:hover:border-purple-700 transition-colors"
          >
            <div className="flex items-center gap-3">
              <Users className="w-5 h-5 text-purple-600 dark:text-purple-400" />
              <div className="text-left">
                <div className="font-medium text-gray-900 dark:text-gray-100">User Management</div>
                <div className="text-sm text-gray-600 dark:text-gray-400">View and manage all users</div>
              </div>
            </div>
            <ChevronRight className="w-5 h-5 text-gray-400" />
          </button>

          <button
            onClick={() => setActiveView('health')}
            className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-green-300 dark:hover:border-green-700 transition-colors"
          >
            <div className="flex items-center gap-3">
              <Heart className="w-5 h-5 text-green-600 dark:text-green-400" />
              <div className="text-left">
                <div className="font-medium text-gray-900 dark:text-gray-100">System Health</div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Monitor system status and performance</div>
              </div>
            </div>
            <ChevronRight className="w-5 h-5 text-gray-400" />
          </button>

          <button
            onClick={() => setActiveView('audit-logs')}
            className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-700 transition-colors"
          >
            <div className="flex items-center gap-3">
              <FileText className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              <div className="text-left">
                <div className="font-medium text-gray-900 dark:text-gray-100">Audit Logs</div>
                <div className="text-sm text-gray-600 dark:text-gray-400">View permission changes and security events</div>
              </div>
            </div>
            <ChevronRight className="w-5 h-5 text-gray-400" />
          </button>

          <button
            onClick={() => setActiveView('founder-setup')}
            className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-yellow-300 dark:hover:border-yellow-700 transition-colors"
          >
            <div className="flex items-center gap-3">
              <Key className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
              <div className="text-left">
                <div className="font-medium text-gray-900 dark:text-gray-100">Founder Setup</div>
                <div className="text-sm text-gray-600 dark:text-gray-400">Configure founder password</div>
              </div>
            </div>
            <ChevronRight className="w-5 h-5 text-gray-400" />
          </button>
        </div>
      </div>
    )
  }

  // Users List View
  if (activeView === 'users') {
    return (
      <div className="space-y-4">
        {/* Back Button */}
        <button
          onClick={() => setActiveView('overview')}
          className="text-sm text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 flex items-center gap-1"
        >
          ← Back to Overview
        </button>

        {/* Users Table */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-700">
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">User</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Role</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Last Login</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {users.map((user) => (
                <tr key={user.user_id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                  <td className="px-4 py-3">
                    <div>
                      <div className="font-medium text-gray-900 dark:text-gray-100">{user.username}</div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">{user.device_id}</div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 text-xs font-medium rounded border ${getRoleBadgeClass(user.role)}`}>
                      {user.role}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      {user.last_login ? formatDate(user.last_login) : 'Never'}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => fetchUserDetails(user)}
                      className="flex items-center gap-1 text-sm text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300"
                    >
                      <Eye className="w-4 h-4" />
                      View Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  // User Detail View
  if (activeView === 'user-detail' && selectedUser) {
    return (
      <div className="space-y-4">
        {/* Back Button */}
        <button
          onClick={() => setActiveView('users')}
          className="text-sm text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 flex items-center gap-1"
        >
          ← Back to Users
        </button>

        {/* User Info */}
        <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{selectedUser.username}</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">{selectedUser.device_id}</p>
            </div>
            <span className={`px-3 py-1 text-sm font-medium rounded border ${getRoleBadgeClass(selectedUser.role)}`}>
              {selectedUser.role}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-gray-500 dark:text-gray-400">User ID</div>
              <div className="font-mono text-gray-900 dark:text-gray-100 text-xs">{selectedUser.user_id}</div>
            </div>
            <div>
              <div className="text-gray-500 dark:text-gray-400">Created</div>
              <div className="text-gray-900 dark:text-gray-100">{formatDate(selectedUser.created_at)}</div>
            </div>
            <div>
              <div className="text-gray-500 dark:text-gray-400">Last Login</div>
              <div className="text-gray-900 dark:text-gray-100">
                {selectedUser.last_login ? formatDate(selectedUser.last_login) : 'Never'}
              </div>
            </div>
            <div>
              <div className="text-gray-500 dark:text-gray-400">Status</div>
              <div className="text-gray-900 dark:text-gray-100">
                {selectedUser.is_active ? 'Active' : 'Inactive'}
              </div>
            </div>
          </div>
        </div>

        {/* User's Chats */}
        <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
            <MessageSquare className="w-4 h-4" />
            Chat Sessions ({userChats.length})
          </h4>

          {userChats.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400">No chat sessions found</p>
          ) : (
            <div className="space-y-2">
              {userChats.map((chat) => (
                <div key={chat.id} className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded border border-gray-200 dark:border-gray-600">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-medium text-gray-900 dark:text-gray-100">{chat.title}</div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        {chat.message_count} messages • Updated {formatDate(chat.updated_at)}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    )
  }

  // System Health View
  if (activeView === 'health') {
    return (
      <div className="space-y-4">
        {/* Back Button */}
        <button
          onClick={() => setActiveView('overview')}
          className="text-sm text-green-600 dark:text-green-400 hover:text-green-700 dark:hover:text-green-300 flex items-center gap-1"
        >
          ← Back to Overview
        </button>

        <SystemHealthDashboard />
      </div>
    )
  }

  // Audit Logs View
  if (activeView === 'audit-logs') {
    return (
      <div className="space-y-4">
        {/* Back Button */}
        <button
          onClick={() => setActiveView('overview')}
          className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 flex items-center gap-1"
        >
          ← Back to Overview
        </button>

        <AuditLogViewer />
      </div>
    )
  }

  // Founder Setup View
  if (activeView === 'founder-setup') {
    return (
      <div className="space-y-4">
        {/* Back Button */}
        <button
          onClick={() => setActiveView('overview')}
          className="text-sm text-yellow-600 dark:text-yellow-400 hover:text-yellow-700 dark:hover:text-yellow-300 flex items-center gap-1"
        >
          ← Back to Overview
        </button>

        <FounderSetupWizard />
      </div>
    )
  }

  return null
}
