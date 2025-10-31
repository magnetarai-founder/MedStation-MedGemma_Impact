import { Shield, User, Eye, EyeOff, Fingerprint, CheckCircle, XCircle } from 'lucide-react'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useDocsStore } from '@/stores/docsStore'
import { authenticateBiometric, isBiometricAvailable, testTouchID } from '@/lib/biometricAuth'
import toast from 'react-hot-toast'

/**
 * Security Tab
 *
 * Displays user role, security information, and vault security settings
 */

interface UserProfile {
  user_id: string
  display_name: string
  device_name: string
  created_at: string
  avatar_color: string | null
  bio: string | null
  role: string
  role_changed_at: string | null
  role_changed_by: string | null
}

const ROLE_DESCRIPTIONS: Record<string, { label: string; description: string; color: string }> = {
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
  viewer: {
    label: 'Viewer',
    description: 'Read-only access to workflows and data.',
    color: 'text-gray-600 dark:text-gray-400'
  }
}

export default function SecurityTab() {
  // Vault security settings
  const { securitySettings, updateSecuritySettings } = useDocsStore()
  const [isTouchIDAvailable, setIsTouchIDAvailable] = useState<boolean | null>(null)
  const [touchIDTestResult, setTouchIDTestResult] = useState<'success' | 'failed' | null>(null)

  // Fetch current user profile
  const { data: currentUser, isLoading } = useQuery({
    queryKey: ['current-user'],
    queryFn: async () => {
      const response = await fetch('/api/v1/users/me')
      if (!response.ok) throw new Error('Failed to load user profile')
      return response.json() as Promise<UserProfile>
    },
  })

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

  const roleInfo = ROLE_DESCRIPTIONS[currentUser.role] || ROLE_DESCRIPTIONS.member

  // Handle Touch ID toggle
  const handleTouchIDToggle = async (enabled: boolean) => {
    if (enabled) {
      // User is trying to enable Touch ID - test if it's available
      toast.loading('Checking Touch ID availability...', { id: 'touchid-check' })

      const available = await isBiometricAvailable()
      setIsTouchIDAvailable(available)

      if (!available) {
        toast.error('Touch ID not available on this device', { id: 'touchid-check' })
        setTouchIDTestResult('failed')
        return
      }

      // Touch ID is available, now test authentication
      toast.loading('Testing Touch ID authentication...', { id: 'touchid-check' })

      const authenticated = await authenticateBiometric()

      if (authenticated) {
        toast.success('Touch ID verified and enabled!', { id: 'touchid-check' })
        setTouchIDTestResult('success')
        updateSecuritySettings({ require_touch_id: true })
      } else {
        toast.error('Touch ID authentication failed', { id: 'touchid-check' })
        setTouchIDTestResult('failed')
      }
    } else {
      // User is disabling Touch ID
      updateSecuritySettings({ require_touch_id: false })
      setTouchIDTestResult(null)
      toast.success('Touch ID disabled')
    }
  }

  // Test Touch ID button
  const handleTestTouchID = async () => {
    toast.loading('Testing Touch ID...', { id: 'touchid-test' })

    const result = await testTouchID()
    if (result) {
      toast.success('Touch ID is available and ready!', { id: 'touchid-test' })
      setTouchIDTestResult('success')
    } else {
      toast.error('Touch ID not available on this device', { id: 'touchid-test' })
      setTouchIDTestResult('failed')
    }
  }

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

      {/* Vault Security Settings */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="w-5 h-5 text-amber-600 dark:text-amber-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Vault Security
          </h3>
        </div>

        <div className="space-y-4">
          {/* Stealth Labels */}
          <div className="border-b border-gray-200 dark:border-gray-700 pb-4">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={securitySettings.stealth_labels}
                onChange={(e) => updateSecuritySettings({ stealth_labels: e.target.checked })}
                className="mt-1 w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-amber-600 focus:ring-amber-500"
              />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    Stealth Labels
                  </span>
                  {securitySettings.stealth_labels ? (
                    <EyeOff className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                  ) : (
                    <Eye className="w-4 h-4 text-gray-400" />
                  )}
                </div>
                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                  Display innocuous cover names for sensitive vault documents. Actual titles are only visible when documents are opened.
                </p>
                <div className="mt-2 p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
                  <p className="text-xs text-amber-800 dark:text-amber-200">
                    <strong>Example:</strong> "Project Budget 2024.xlsx" → "Grocery List.txt"
                  </p>
                  <p className="text-xs text-amber-700 dark:text-amber-300 mt-1">
                    Provides plausible deniability if device is searched. Real title visible only after unlocking document.
                  </p>
                </div>
              </div>
            </label>
          </div>

          {/* Decoy Mode */}
          <div className="border-b border-gray-200 dark:border-gray-700 pb-4">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={securitySettings.decoy_mode_enabled}
                onChange={(e) => updateSecuritySettings({ decoy_mode_enabled: e.target.checked })}
                className="mt-1 w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-amber-600 focus:ring-amber-500"
              />
              <div className="flex-1">
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  Decoy Vault Mode
                </div>
                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                  Enable dual vault storage: real vault (sensitive data) + decoy vault (innocuous data). Each unlocks with a different password.
                </p>
                <div className="mt-2 p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
                  <p className="text-xs text-amber-800 dark:text-amber-200">
                    When enabled, you can configure a second password that unlocks a decoy vault containing non-sensitive documents.
                  </p>
                </div>
              </div>
            </label>
          </div>

          {/* Touch ID Requirement */}
          <div className="border-b border-gray-200 dark:border-gray-700 pb-4">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={securitySettings.require_touch_id}
                onChange={(e) => handleTouchIDToggle(e.target.checked)}
                className="mt-1 w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-amber-600 focus:ring-amber-500"
              />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    Require Touch ID
                  </span>
                  {touchIDTestResult === 'success' && (
                    <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />
                  )}
                  {touchIDTestResult === 'failed' && (
                    <XCircle className="w-4 h-4 text-red-600 dark:text-red-400" />
                  )}
                </div>
                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                  Require biometric authentication (Touch ID/Face ID) before password entry when unlocking vault.
                </p>
                {securitySettings.require_touch_id && (
                  <div className="mt-3">
                    <button
                      onClick={handleTestTouchID}
                      className="inline-flex items-center gap-2 px-3 py-1.5 text-xs bg-amber-100 hover:bg-amber-200 dark:bg-amber-900/30 dark:hover:bg-amber-900/50 text-amber-800 dark:text-amber-200 rounded-lg transition-colors"
                    >
                      <Fingerprint className="w-4 h-4" />
                      Test Touch ID
                    </button>
                  </div>
                )}
                {isTouchIDAvailable === false && (
                  <div className="mt-2 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                    <p className="text-xs text-red-800 dark:text-red-200">
                      Touch ID is not available on this device. Make sure your Mac has Touch ID enabled in System Preferences.
                    </p>
                  </div>
                )}
              </div>
            </label>
          </div>

          {/* Disable Screenshots */}
          <div className="border-b border-gray-200 dark:border-gray-700 pb-4">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={securitySettings.disable_screenshots}
                onChange={(e) => updateSecuritySettings({ disable_screenshots: e.target.checked })}
                className="mt-1 w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-amber-600 focus:ring-amber-500"
              />
              <div className="flex-1">
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  Disable Screenshots
                </div>
                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                  Prevent screen captures of vault content for additional security.
                </p>
              </div>
            </label>
          </div>

          {/* Auto-lock Settings */}
          <div>
            <div className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
              Auto-lock Vault
            </div>
            <div className="space-y-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={securitySettings.lock_on_exit}
                  onChange={(e) => updateSecuritySettings({ lock_on_exit: e.target.checked })}
                  className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-amber-600 focus:ring-amber-500"
                />
                <span className="text-xs text-gray-900 dark:text-gray-100">
                  Lock vault when closing app
                </span>
              </label>

              <div>
                <label className="block text-xs text-gray-900 dark:text-gray-100 mb-1">
                  Lock after inactivity:
                </label>
                <select
                  value={securitySettings.inactivity_lock}
                  onChange={(e) => updateSecuritySettings({ inactivity_lock: e.target.value as any })}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                >
                  <option value="instant">Instantly</option>
                  <option value="30s">30 seconds</option>
                  <option value="1m">1 minute</option>
                  <option value="2m">2 minutes</option>
                  <option value="3m">3 minutes</option>
                  <option value="4m">4 minutes</option>
                  <option value="5m">5 minutes</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
