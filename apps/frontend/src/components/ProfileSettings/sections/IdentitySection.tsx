/**
 * IdentitySection Component
 *
 * User identity and profile management section
 */

import { useState } from 'react'
import { Save, Copy, Check, Shield, Briefcase } from 'lucide-react'
import { ROLES } from '@/lib/roles'
import { formatRole, getRoleDescription, getRoleColor } from '@/lib/roles'
import toast from 'react-hot-toast'
import { SectionHeader } from '../components/SectionHeader'
import type { UserProfile, ProfileFormState, ProfileFormHandlers } from '../types'

interface IdentitySectionProps {
  user: UserProfile
  formState: ProfileFormState
  handlers: ProfileFormHandlers
}

export function IdentitySection({ user, formState, handlers }: IdentitySectionProps) {
  const [copiedUserId, setCopiedUserId] = useState(false)

  const handleCopyUserId = () => {
    if (user?.user_id) {
      navigator.clipboard.writeText(user.user_id)
      setCopiedUserId(true)
      toast.success('User ID copied to clipboard')
      setTimeout(() => setCopiedUserId(false), 2000)
    }
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        title="User Identity"
        description="Manage your profile and device information"
      />

      <div className="space-y-4">
        {/* Display Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Display Name
          </label>
          <input
            type="text"
            value={formState.displayName}
            onChange={(e) => handlers.setDisplayName(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            placeholder="Your name"
          />
        </div>

        {/* Device Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Device Name
          </label>
          <input
            type="text"
            value={formState.deviceName}
            onChange={(e) => handlers.setDeviceName(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            placeholder="Your device"
          />
        </div>

        {/* Avatar Color */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Avatar Color
          </label>
          <div className="flex items-center gap-3">
            <input
              type="color"
              value={formState.avatarColor}
              onChange={(e) => handlers.setAvatarColor(e.target.value)}
              className="w-12 h-12 rounded-lg border border-gray-300 dark:border-gray-600 cursor-pointer"
            />
            <span className="text-sm text-gray-600 dark:text-gray-400">{formState.avatarColor}</span>
          </div>
        </div>

        {/* Bio */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Bio
          </label>
          <textarea
            value={formState.bio}
            onChange={(e) => handlers.setBio(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 resize-none"
            placeholder="Tell others about yourself..."
            rows={3}
          />
        </div>

        {/* User ID (read-only) */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            User ID
          </label>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={user?.user_id || ''}
              readOnly
              className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-900/50 text-gray-600 dark:text-gray-400 font-mono text-sm"
            />
            <button
              onClick={handleCopyUserId}
              className="p-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors"
              title="Copy User ID"
            >
              {copiedUserId ? (
                <Check className="w-5 h-5 text-green-600" />
              ) : (
                <Copy className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              )}
            </button>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Unique identifier for P2P LAN/mesh connections (local network only)
          </p>
        </div>

        {/* Role & Permissions (read-only) */}
        {user?.role && (
          <div className="p-4 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <label className="block text-sm font-medium text-blue-900 dark:text-blue-100 mb-3">
              Role & Permissions
            </label>

            <div className="flex items-center gap-3 mb-3">
              <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-semibold ${getRoleColor(user.role)}`}>
                    {formatRole(user.role)}
                  </span>
                </div>
                <div className="text-xs text-blue-700 dark:text-blue-300 mt-1">
                  {getRoleDescription(user.role)}
                </div>
              </div>
            </div>

            {user.role_changed_at && (
              <div className="text-xs text-blue-600 dark:text-blue-400 pt-3 border-t border-blue-200 dark:border-blue-800">
                <p>Role assigned: {new Date(user.role_changed_at).toLocaleDateString()}</p>
                {user.role_changed_by && <p>Assigned by: {user.role_changed_by}</p>}
              </div>
            )}
          </div>
        )}

        {/* Job Role (Phase 5.1) */}
        <div className="p-4 bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-lg border border-green-200 dark:border-green-800">
          <div className="flex items-start gap-3">
            <Briefcase className="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5" />
            <div className="flex-1">
              <div className="text-sm font-semibold text-green-900 dark:text-green-100 mb-1">
                Job Role
              </div>
              <p className="text-xs text-green-700 dark:text-green-300 mb-3">
                {user?.role === ROLES.GOD_RIGHTS || user?.role === ROLES.SUPER_ADMIN
                  ? 'Your job role is automatically set based on your system role and cannot be changed'
                  : 'Your job role is used for workflow permissions and queue access control'}
              </p>

              {user?.role === ROLES.GOD_RIGHTS || user?.role === ROLES.SUPER_ADMIN ? (
                <div className="px-3 py-2 bg-gray-100 dark:bg-gray-800/50 border border-green-300 dark:border-green-700 rounded-lg text-sm text-gray-700 dark:text-gray-300 font-medium">
                  {user?.job_role || 'Unassigned'}
                </div>
              ) : (
                <select
                  value={formState.jobRole}
                  onChange={(e) => handlers.setJobRole(e.target.value)}
                  className="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-green-300 dark:border-green-700 rounded-lg text-sm text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-green-500 focus:border-green-500"
                >
                  <option value="unassigned">Unassigned</option>
                  <option value="doctor">Doctor</option>
                  <option value="pastor">Pastor</option>
                  <option value="nurse">Nurse</option>
                  <option value="admin_staff">Admin Staff</option>
                  <option value="volunteer">Volunteer</option>
                </select>
              )}

              <p className="text-xs text-green-600 dark:text-green-400 mt-2">
                Current: <span className="font-semibold">{user?.job_role || formState.jobRole === 'admin_staff' ? 'Admin Staff' : (formState.jobRole?.charAt(0).toUpperCase() + formState.jobRole?.slice(1)) || 'Unassigned'}</span>
              </p>
            </div>
          </div>
        </div>

        {/* Save Button */}
        {formState.hasUnsavedChanges && (
          <button
            onClick={handlers.handleSave}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors"
          >
            <Save className="w-4 h-4" />
            <span>Save Changes</span>
          </button>
        )}
      </div>
    </div>
  )
}
