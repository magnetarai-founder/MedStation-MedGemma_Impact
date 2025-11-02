import { Shield, User } from 'lucide-react'
import { useUserStore } from '@/stores/userStore'

/**
 * Security Tab
 *
 * Displays user role, security information, and vault security settings
 */

const ROLE_DESCRIPTIONS: Record<string, { label: string; description: string; color: string }> = {
  founder_rights: {
    label: 'Founder Rights',
    description: 'System founder with unrestricted access to all features and settings.',
    color: 'text-purple-600 dark:text-purple-400'
  },
  super_admin: {
    label: 'Super Admin',
    description: 'Full system access. Can manage all users, workflows, and settings.',
    color: 'text-red-600 dark:text-red-400'
  },
  admin: {
    label: 'Admin',
    description: 'Can manage users and workflows, but cannot create other admins.',
    color: 'text-orange-600 dark:text-orange-400'
  },
  member: {
    label: 'Member',
    description: 'Can create and edit own workflows.',
    color: 'text-blue-600 dark:text-blue-400'
  },
  guest: {
    label: 'Guest',
    description: 'Limited access to workflows and data.',
    color: 'text-gray-600 dark:text-gray-400'
  }
}

export default function SecurityTab() {
  // Use userStore instead of separate API call
  const { user: currentUser, isLoading } = useUserStore()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  if (!currentUser) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500 dark:text-gray-400">
        <p>Failed to load user information</p>
      </div>
    )
  }

  const roleInfo = ROLE_DESCRIPTIONS[currentUser.role || 'member'] || ROLE_DESCRIPTIONS.member

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-3">
        <Shield className="w-6 h-6 text-blue-500" />
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Security & Permissions
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Your role and access level
          </p>
        </div>
      </div>

      {/* Current User Info */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="flex items-start space-x-4">
          <div className={`w-12 h-12 rounded-full flex items-center justify-center ${currentUser.avatar_color ? '' : 'bg-blue-500'}`}
               style={{ backgroundColor: currentUser.avatar_color || undefined }}>
            <User className="w-6 h-6 text-white" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {currentUser.display_name}
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {currentUser.device_name}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
              User ID: {currentUser.user_id}
            </p>
          </div>
        </div>
      </div>

      {/* Role Badge */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Access Role
          </h3>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${roleInfo.color} bg-opacity-10`}
                style={{ backgroundColor: `${roleInfo.color.split(' ')[0].replace('text-', '')}15` }}>
            {roleInfo.label}
          </span>
        </div>

        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          {roleInfo.description}
        </p>

        {currentUser.role_changed_at && (
          <div className="text-xs text-gray-500 dark:text-gray-500 pt-4 border-t border-gray-200 dark:border-gray-700">
            <p>Role last changed: {new Date(currentUser.role_changed_at).toLocaleString()}</p>
            {currentUser.role_changed_by && (
              <p>Changed by: {currentUser.role_changed_by}</p>
            )}
          </div>
        )}
      </div>

      {/* Security Features Info */}
      <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-6 border border-blue-200 dark:border-blue-800">
        <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-2">
          Security Features Enabled
        </h3>
        <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
          <li>• End-to-end encryption for P2P messaging</li>
          <li>• Database encryption at rest (AES-256-GCM)</li>
          <li>• Role-based access control (RBAC)</li>
          <li>• Secure key storage (macOS Keychain)</li>
          <li>• Automatic audit logging</li>
        </ul>
        <p className="text-xs text-blue-700 dark:text-blue-300 mt-4">
          These security features are enabled system-wide and managed automatically.
        </p>
      </div>

      {/* Account Info */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          Account Information
        </h3>
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-gray-600 dark:text-gray-400">Account Created:</dt>
            <dd className="text-gray-900 dark:text-gray-100">
              {new Date(currentUser.created_at).toLocaleDateString()}
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-600 dark:text-gray-400">Device Name:</dt>
            <dd className="text-gray-900 dark:text-gray-100">{currentUser.device_name}</dd>
          </div>
          {currentUser.bio && (
            <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
              <dt className="text-gray-600 dark:text-gray-400 mb-1">Bio:</dt>
              <dd className="text-gray-900 dark:text-gray-100">{currentUser.bio}</dd>
            </div>
          )}
        </dl>
      </div>

      {/* Note about Vault Security */}
      <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-6 border border-blue-200 dark:border-blue-800">
        <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-2">
          💡 Configure Vault Security
        </h3>
        <p className="text-sm text-blue-800 dark:text-blue-200">
          To configure vault security settings (Touch ID, stealth labels, decoy mode, auto-lock, screenshots),
          go to <strong>Profile → Security</strong> tab.
        </p>
      </div>
    </div>
  )
}
