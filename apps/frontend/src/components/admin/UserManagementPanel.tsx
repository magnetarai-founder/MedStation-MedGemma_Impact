/**
 * User Management Panel
 *
 * Admin-only component for managing user roles and permissions
 * Requires 'super_admin' or 'admin' role to access
 */

import { useState, useEffect } from 'react'
import { Shield, Users, Crown, Eye, UserPlus, Trash2, Calendar, AlertCircle } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'

interface User {
  user_id: string
  display_name: string
  device_name: string
  created_at: string
  role: string
  role_changed_at: string | null
  role_changed_by: string | null
}

interface RoleBadgeProps {
  role: string
}

function RoleBadge({ role }: RoleBadgeProps) {
  const getRoleConfig = (role: string) => {
    switch (role) {
      case 'super_admin':
        return {
          icon: Crown,
          label: 'Super Admin',
          className: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800'
        }
      case 'admin':
        return {
          icon: Shield,
          label: 'Admin',
          className: 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 border-orange-200 dark:border-orange-800'
        }
      case 'member':
        return {
          icon: Users,
          label: 'Member',
          className: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-800'
        }
      case 'viewer':
        return {
          icon: Eye,
          label: 'Viewer',
          className: 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-600'
        }
      default:
        return {
          icon: Users,
          label: role,
          className: 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-600'
        }
    }
  }

  const config = getRoleConfig(role)
  const Icon = config.icon

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${config.className}`}>
      <Icon className="w-3 h-3" />
      {config.label}
    </span>
  )
}

export function UserManagementPanel() {
  const queryClient = useQueryClient()

  // Fetch current user to check permissions
  const { data: currentUser } = useQuery({
    queryKey: ['current-user'],
    queryFn: async () => {
      const response = await fetch('/api/v1/users/me')
      if (!response.ok) throw new Error('Failed to load user profile')
      return response.json() as Promise<User>
    },
  })

  // Fetch all team members (mock for now)
  const { data: users = [], isLoading } = useQuery({
    queryKey: ['team-members'],
    queryFn: async () => {
      // TODO: Replace with actual API call when backend is ready
      // const response = await fetch('/api/v1/teams/members')
      // const data = await response.json()
      // return data as User[]

      // Mock data for now
      return [
        {
          user_id: currentUser?.user_id || '1',
          display_name: currentUser?.display_name || 'Field Worker',
          device_name: currentUser?.device_name || 'MacBook Pro',
          created_at: currentUser?.created_at || new Date().toISOString(),
          role: currentUser?.role || 'super_admin',
          role_changed_at: null,
          role_changed_by: null,
        },
        {
          user_id: '2',
          display_name: 'Sarah Chen',
          device_name: 'iPhone 14',
          created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
          role: 'admin',
          role_changed_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
          role_changed_by: currentUser?.user_id || '1',
        },
        {
          user_id: '3',
          display_name: 'Mike Rodriguez',
          device_name: 'iPad Pro',
          created_at: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
          role: 'member',
          role_changed_at: null,
          role_changed_by: null,
        },
        {
          user_id: '4',
          display_name: 'Emily Johnson',
          device_name: 'Android Phone',
          created_at: new Date(Date.now() - 21 * 24 * 60 * 60 * 1000).toISOString(),
          role: 'viewer',
          role_changed_at: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
          role_changed_by: '2',
        },
      ] as User[]
    },
    enabled: !!currentUser,
  })

  // Update user role mutation
  const updateRoleMutation = useMutation({
    mutationFn: async ({ userId, newRole }: { userId: string; newRole: string }) => {
      // TODO: Replace with actual API call
      // await fetch(`/api/v1/users/${userId}/role`, {
      //   method: 'PUT',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ role: newRole })
      // })

      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 500))
      return { userId, newRole }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['team-members'] })
      toast.success('User role updated successfully')
    },
    onError: (error) => {
      console.error('Failed to update user role:', error)
      toast.error('Failed to update user role')
    },
  })

  function handleRoleChange(userId: string, newRole: string, userName: string) {
    if (!confirm(`Change role for "${userName}" to "${newRole}"?`)) {
      return
    }

    updateRoleMutation.mutate({ userId, newRole })
  }

  function formatDate(dateString: string) {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffDays < 1) return 'Today'
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} week${Math.floor(diffDays / 7) > 1 ? 's' : ''} ago`

    return date.toLocaleDateString()
  }

  // Check if current user has admin permissions
  const canManageTeam = currentUser?.role === 'super_admin' || currentUser?.role === 'admin'

  if (!currentUser) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  if (!canManageTeam) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-500 dark:text-gray-400">
        <Shield className="w-16 h-16 mb-4 opacity-50" />
        <h3 className="text-lg font-semibold mb-2">Access Denied</h3>
        <p className="text-sm text-center max-w-md">
          Only administrators can access the user management panel.
          Your current role: <RoleBadge role={currentUser.role} />
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
        <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
        <div>
          <h4 className="font-semibold text-blue-900 dark:text-blue-100 mb-1">
            User Management
          </h4>
          <p className="text-sm text-blue-700 dark:text-blue-300">
            Manage user roles and permissions for your team. Changes take effect immediately.
          </p>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-700">
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  User
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Role
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Joined
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {users.map((user) => (
                <tr
                  key={user.user_id}
                  className="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors"
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center">
                        <Users className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                      </div>
                      <div>
                        <div className="font-medium text-gray-900 dark:text-gray-100">
                          {user.display_name}
                          {user.user_id === currentUser.user_id && (
                            <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">(You)</span>
                          )}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          {user.device_name}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <RoleBadge role={user.role} />
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-1.5 text-sm text-gray-600 dark:text-gray-400">
                      <Calendar className="w-4 h-4" />
                      {formatDate(user.created_at)}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    {user.user_id !== currentUser.user_id && (
                      <select
                        value={user.role}
                        onChange={(e) => handleRoleChange(user.user_id, e.target.value, user.display_name)}
                        disabled={updateRoleMutation.isPending}
                        className="px-3 py-1.5 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600
                                 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500
                                 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <option value="viewer">Viewer</option>
                        <option value="member">Member</option>
                        <option value="admin">Admin</option>
                        {currentUser.role === 'super_admin' && (
                          <option value="super_admin">Super Admin</option>
                        )}
                      </select>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-semibold text-amber-900 dark:text-amber-100 mb-1">
              Role Permissions
            </p>
            <ul className="text-amber-700 dark:text-amber-300 space-y-1">
              <li><strong>Viewer:</strong> Read-only access to workflows and data</li>
              <li><strong>Member:</strong> Can create and edit own workflows</li>
              <li><strong>Admin:</strong> Can manage users and workflows (cannot create other admins)</li>
              <li><strong>Super Admin:</strong> Full system access including user management</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
