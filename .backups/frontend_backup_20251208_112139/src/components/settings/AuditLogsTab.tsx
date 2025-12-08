/**
 * Audit Logs Tab Component
 *
 * Admin-only component for viewing system audit logs
 * Requires 'super_admin' or 'admin' role to access
 */

import { useState, useEffect } from 'react'
import { Shield, FileText, Download, Calendar, User, Activity, Globe, AlertCircle, Search } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import toast from 'react-hot-toast'

interface AuditLog {
  id: string
  timestamp: string
  user_id: string
  user_name: string
  action: string
  resource: string
  resource_id: string
  ip_address: string
  user_agent: string
  status: 'success' | 'failed'
}

interface UserSuggestion {
  user_id: string
  username: string
}

export default function AuditLogsTab() {
  // Read filters from URL on mount
  const urlParams = new URLSearchParams(window.location.search)
  const [userFilter, setUserFilter] = useState(urlParams.get('user') || '')
  const [actionFilter, setActionFilter] = useState(urlParams.get('action') || '')
  const [startDate, setStartDate] = useState(urlParams.get('start_date') || '')
  const [endDate, setEndDate] = useState(urlParams.get('end_date') || '')
  const [showUserSuggestions, setShowUserSuggestions] = useState(false)

  // Persist filters to URL whenever they change
  useEffect(() => {
    const params = new URLSearchParams()
    if (userFilter) params.set('user', userFilter)
    if (actionFilter) params.set('action', actionFilter)
    if (startDate) params.set('start_date', startDate)
    if (endDate) params.set('end_date', endDate)

    const newUrl = params.toString()
      ? `${window.location.pathname}?${params}`
      : window.location.pathname

    window.history.replaceState({}, '', newUrl)
  }, [userFilter, actionFilter, startDate, endDate])

  // Fetch current user to check permissions
  const { data: currentUser } = useQuery({
    queryKey: ['current-user'],
    queryFn: async () => {
      const response = await fetch('/api/v1/users/me')
      if (!response.ok) throw new Error('Failed to load user profile')
      return response.json()
    },
  })

  // Fetch user list for autosuggest
  const { data: users = [] } = useQuery<UserSuggestion[]>({
    queryKey: ['admin-users'],
    queryFn: async () => {
      const response = await fetch('/api/v1/admin/users')
      if (!response.ok) return []
      const data = await response.json()
      return data.users?.map((u: any) => ({
        user_id: u.user_id,
        username: u.username
      })) || []
    },
    enabled: !!currentUser,
  })

  // Filter users based on input
  const filteredUsers = users.filter(u =>
    u.username.toLowerCase().includes(userFilter.toLowerCase()) ||
    u.user_id.toLowerCase().includes(userFilter.toLowerCase())
  ).slice(0, 5)

  // Fetch audit logs with filters
  const { data: logsResponse, isLoading } = useQuery({
    queryKey: ['audit-logs', userFilter, actionFilter, startDate, endDate],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (userFilter) params.set('user_id', userFilter)
      if (actionFilter) params.set('action', actionFilter)
      if (startDate) params.set('start_date', startDate)
      if (endDate) params.set('end_date', endDate)
      params.set('limit', '100')
      params.set('offset', '0')

      const response = await fetch(`/api/v1/admin/audit/logs?${params}`)
      if (!response.ok) {
        if (response.status === 403) {
          throw new Error('Insufficient permissions to view audit logs')
        }
        throw new Error('Failed to load audit logs')
      }
      const data = await response.json()
      return data as { logs: AuditLog[], total: number }
    },
    enabled: !!currentUser,
  })

  const logs = logsResponse?.logs || []

  function handleExportCSV() {
    if (logs.length === 0) {
      toast.error('No logs to export')
      return
    }

    // Use backend export endpoint
    const params = new URLSearchParams()
    if (startDate) params.set('start_date', startDate)
    if (endDate) params.set('end_date', endDate)

    const exportUrl = `/api/v1/admin/audit/export?${params}`

    // Create hidden link to trigger download
    const link = document.createElement('a')
    link.href = exportUrl
    link.download = `audit-logs-${new Date().toISOString().split('T')[0]}.csv`
    link.style.display = 'none'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    toast.success('Audit logs exported successfully')
  }

  function formatDateTime(dateString: string) {
    const date = new Date(dateString)
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    })
  }

  function formatTimeAgo(dateString: string) {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    return `${diffDays}d ago`
  }

  function getActionColor(action: string) {
    if (action.includes('create') || action.includes('invite')) {
      return 'text-green-600 dark:text-green-400'
    }
    if (action.includes('delete') || action.includes('revoke')) {
      return 'text-red-600 dark:text-red-400'
    }
    if (action.includes('update') || action.includes('modify')) {
      return 'text-amber-600 dark:text-amber-400'
    }
    if (action.includes('login') || action.includes('auth')) {
      return 'text-blue-600 dark:text-blue-400'
    }
    return 'text-gray-600 dark:text-gray-400'
  }

  function clearFilters() {
    setUserFilter('')
    setActionFilter('')
    setStartDate('')
    setEndDate('')
  }

  // Check if current user has admin permissions
  const canViewAuditLogs = currentUser?.role === 'super_admin' || currentUser?.role === 'admin'

  if (!currentUser) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  if (!canViewAuditLogs) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-500 dark:text-gray-400">
        <Shield className="w-16 h-16 mb-4 opacity-50" />
        <h3 className="text-lg font-semibold mb-2">Access Denied</h3>
        <p className="text-sm text-center max-w-md">
          Only administrators can access audit logs.
          Your current role: <span className="font-medium">{currentUser.role}</span>
        </p>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-3 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
        <FileText className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
        <div>
          <h4 className="font-semibold text-blue-900 dark:text-blue-100 mb-1">
            System Audit Logs
          </h4>
          <p className="text-sm text-blue-700 dark:text-blue-300">
            Track all system activities including user actions, authentication events, and data access.
            Logs are retained for 90 days for compliance purposes.
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <Search className="w-4 h-4" />
            Filters
          </h3>
          <button
            onClick={clearFilters}
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
          >
            Clear all
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="relative">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              User
            </label>
            <input
              type="text"
              value={userFilter}
              onChange={(e) => {
                setUserFilter(e.target.value)
                setShowUserSuggestions(true)
              }}
              onFocus={() => setShowUserSuggestions(true)}
              onBlur={() => setTimeout(() => setShowUserSuggestions(false), 200)}
              placeholder="Search by username or user ID..."
              className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600
                       rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {/* User suggestions dropdown */}
            {showUserSuggestions && userFilter && filteredUsers.length > 0 && (
              <div className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                {filteredUsers.map(user => (
                  <button
                    key={user.user_id}
                    onClick={() => {
                      setUserFilter(user.user_id)
                      setShowUserSuggestions(false)
                    }}
                    className="w-full px-3 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                  >
                    <div className="font-medium text-gray-900 dark:text-gray-100">{user.username}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">{user.user_id}</div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Action
            </label>
            <input
              type="text"
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              placeholder="Search by action..."
              className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600
                       rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Start Date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600
                       rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              End Date
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600
                       rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Export button */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-600 dark:text-gray-400">
          Showing <span className="font-semibold">{logs.length}</span> log{logs.length !== 1 ? 's' : ''}
        </div>
        <button
          onClick={handleExportCSV}
          disabled={logs.length === 0}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium
                   disabled:opacity-50 disabled:cursor-not-allowed transition-colors
                   flex items-center gap-2"
        >
          <Download className="w-4 h-4" />
          Export CSV
        </button>
      </div>

      {/* Logs table */}
      {logs.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <FileText className="w-12 h-12 mx-auto mb-3 text-gray-400" />
          <p className="text-gray-600 dark:text-gray-400">No audit logs found</p>
          <p className="text-sm text-gray-500 dark:text-gray-500 mt-1">
            Try adjusting your filters or check back later
          </p>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-700">
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Timestamp
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    User
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Action
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Resource
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    IP Address
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {logs.map((log) => (
                  <tr
                    key={log.id}
                    className="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors"
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div>
                        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {formatDateTime(log.timestamp)}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          {formatTimeAgo(log.timestamp)}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <User className="w-4 h-4 text-gray-400" />
                        <span className="text-sm text-gray-900 dark:text-gray-100">
                          {log.user_name}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <Activity className="w-4 h-4 text-gray-400" />
                        <span className={`text-sm font-medium ${getActionColor(log.action)}`}>
                          {log.action}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        <div>{log.resource}</div>
                        <div className="text-xs text-gray-500 dark:text-gray-500">
                          {log.resource_id}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <Globe className="w-4 h-4 text-gray-400" />
                        <span className="text-sm text-gray-600 dark:text-gray-400">
                          {log.ip_address}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${
                          log.status === 'success'
                            ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                            : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                        }`}
                      >
                        {log.status === 'success' ? 'Success' : 'Failed'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-semibold text-amber-900 dark:text-amber-100 mb-1">
              Audit Log Retention
            </p>
            <ul className="text-amber-700 dark:text-amber-300 space-y-1">
              <li>• Audit logs are retained for 90 days for compliance purposes</li>
              <li>• Export logs regularly for long-term archival</li>
              <li>• Failed authentication attempts are highlighted for security monitoring</li>
              <li>• All sensitive operations (vault access, role changes) are logged</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
