/**
 * Profile Settings Component
 *
 * Global user profile and settings - integrated into SettingsModal
 * Includes: Identity, Security, Updates, Privacy, Danger Zone
 */

import { useState, useEffect, useRef } from 'react'
import { ROLES } from '@/lib/roles'
import {
  User,
  Shield,
  Cloud,
  Eye,
  AlertTriangle,
  Save,
  Copy,
  Check,
  Fingerprint,
  Lock,
  Camera,
  FileDown,
  FileUp,
  RefreshCw,
  Trash2,
  Heart,
  Building2,
  Church,
  ChevronRight,
  CheckCircle,
  XCircle,
  Briefcase,
} from 'lucide-react'
import { useUserStore } from '@/stores/userStore'
import { useDocsStore } from '@/stores/docsStore'
import { isBiometricAvailable, registerBiometric, hasBiometricCredential } from '@/lib/biometricAuth'
import { formatRole, getRoleDescription, getRoleColor } from '@/lib/roles'
import toast from 'react-hot-toast'

type ProfileTab = 'identity' | 'security' | 'updates' | 'privacy' | 'danger'

export function ProfileSettings() {
  const { user, fetchUser, updateUser, resetUser, isLoading } = useUserStore()
  const { securitySettings, updateSecuritySettings } = useDocsStore()
  const hasFetchedRef = useRef(false)

  const [activeTab, setActiveTab] = useState<ProfileTab>('identity')
  const [displayName, setDisplayName] = useState(user?.display_name || '')
  const [deviceName, setDeviceName] = useState(user?.device_name || '')
  const [avatarColor, setAvatarColor] = useState(user?.avatar_color || '#3b82f6')
  const [bio, setBio] = useState(user?.bio || '')
  const [jobRole, setJobRole] = useState(user?.job_role || 'unassigned')
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [copiedUserId, setCopiedUserId] = useState(false)

  // (Cloud/SaaS state removed - offline-only policy)

  // Biometric state
  const [biometricAvailable, setBiometricAvailable] = useState(false)
  const [biometricRegistered, setBiometricRegistered] = useState(false)
  const [checkingBiometric, setCheckingBiometric] = useState(true)

  // Auto-fetch user on mount if not loaded (run only once)
  useEffect(() => {
    if (!user && !isLoading && !hasFetchedRef.current) {
      hasFetchedRef.current = true
      fetchUser()
    }
  }, [user, isLoading, fetchUser])

  // Check biometric availability on mount
  useEffect(() => {
    const checkBiometric = async () => {
      setCheckingBiometric(true)
      const available = await isBiometricAvailable()
      setBiometricAvailable(available)

      if (available && user?.user_id) {
        const registered = hasBiometricCredential(`vault-${user.user_id}`)
        setBiometricRegistered(registered)
      }

      setCheckingBiometric(false)
    }

    if (user?.user_id) {
      checkBiometric()
    }
  }, [user?.user_id])

  // Update local state when user changes
  useEffect(() => {
    if (user) {
      setDisplayName(user.display_name || '')
      setDeviceName(user.device_name || '')
      setAvatarColor(user.avatar_color || '#3b82f6')
      setBio(user.bio || '')
      setJobRole(user.job_role || 'unassigned')
    }
  }, [user])

  const handleSaveProfile = async () => {
    try {
      await updateUser({
        display_name: displayName,
        device_name: deviceName,
        avatar_color: avatarColor,
        bio: bio,
        job_role: jobRole,
      })
      setHasUnsavedChanges(false)
      toast.success('Profile updated successfully')
    } catch (error) {
      toast.error('Failed to update profile')
      console.error('Profile update error:', error)
    }
  }

  const handleCopyUserId = () => {
    if (user?.user_id) {
      navigator.clipboard.writeText(user.user_id)
      setCopiedUserId(true)
      toast.success('User ID copied to clipboard')
      setTimeout(() => setCopiedUserId(false), 2000)
    }
  }

  const handleResetIdentity = async () => {
    if (confirm('Reset your user identity? This will generate a new User ID. Your data will be preserved.')) {
      try {
        await resetUser()
        toast.success('User identity reset')
      } catch (error) {
        toast.error('Failed to reset identity')
      }
    }
  }

  const handleDeleteAllData = () => {
    if (
      confirm(
        'Delete ALL local data? This will remove all documents, chats, and files. Settings will be preserved. This cannot be undone.'
      )
    ) {
      toast.error('Delete all data - Coming soon')
      // TODO: Implement data deletion
    }
  }

  const handleFactoryReset = () => {
    if (
      confirm(
        'FACTORY RESET? This will delete everything - all data, settings, and user identity. This cannot be undone.'
      )
    ) {
      toast.error('Factory reset - Coming soon')
      // TODO: Implement factory reset
    }
  }

  const handleExportData = () => {
    toast('Export data - Coming soon')
  }

  const handleImportBackup = () => {
    toast('Import backup - Coming soon')
  }

  // (handleActivateLicense removed - offline-only policy)

  const handleRegisterBiometric = async () => {
    if (!user?.user_id) {
      toast.error('User ID not found')
      return
    }

    const success = await registerBiometric(`vault-${user.user_id}`, user.user_id)
    if (success) {
      setBiometricRegistered(true)
      toast.success('Touch ID registered successfully')
    }
  }

  const tabs = [
    { id: 'identity' as const, label: 'Identity', icon: User },
    { id: 'security' as const, label: 'Security', icon: Shield },
    { id: 'updates' as const, label: 'Updates', icon: Cloud },
    { id: 'privacy' as const, label: 'Privacy', icon: Eye },
    { id: 'danger' as const, label: 'Danger Zone', icon: AlertTriangle },
  ]

  // Show loading only if actively loading AND no user data
  if (isLoading && !user) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading profile...</p>
        </div>
      </div>
    )
  }

  // If no user after loading, try to fetch and show error
  if (!user) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">Failed to load user profile</p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">Make sure the backend server is running</p>
          <button
            onClick={async () => {
              const { fetchUser } = useUserStore.getState()
              await fetchUser()
            }}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="flex gap-2 flex-wrap">
        {tabs.map((tab) => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 shadow-sm'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          )
        })}
      </div>

      {/* Tab Content */}
      <div className="bg-white dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        {/* Identity Tab */}
        {activeTab === 'identity' && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
                User Identity
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Manage your profile and device information
              </p>
            </div>

            <div className="space-y-4">
              {/* Display Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Display Name
                </label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => {
                    setDisplayName(e.target.value)
                    setHasUnsavedChanges(true)
                  }}
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
                  value={deviceName}
                  onChange={(e) => {
                    setDeviceName(e.target.value)
                    setHasUnsavedChanges(true)
                  }}
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
                    value={avatarColor}
                    onChange={(e) => {
                      setAvatarColor(e.target.value)
                      setHasUnsavedChanges(true)
                    }}
                    className="w-12 h-12 rounded-lg border border-gray-300 dark:border-gray-600 cursor-pointer"
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-400">{avatarColor}</span>
                </div>
              </div>

              {/* Bio */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Bio
                </label>
                <textarea
                  value={bio}
                  onChange={(e) => {
                    setBio(e.target.value)
                    setHasUnsavedChanges(true)
                  }}
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
                        value={jobRole}
                        onChange={(e) => {
                          setJobRole(e.target.value)
                          setHasUnsavedChanges(true)
                        }}
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
                      Current: <span className="font-semibold">{user?.job_role || jobRole === 'admin_staff' ? 'Admin Staff' : (jobRole?.charAt(0).toUpperCase() + jobRole?.slice(1)) || 'Unassigned'}</span>
                    </p>
                  </div>
                </div>
              </div>

              {/* Save Button */}
              {hasUnsavedChanges && (
                <button
                  onClick={handleSaveProfile}
                  className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors"
                >
                  <Save className="w-4 h-4" />
                  <span>Save Changes</span>
                </button>
              )}
            </div>
          </div>
        )}

        {/* Security Tab */}
        {activeTab === 'security' && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
                Security & Authentication
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Configure Touch ID and document security settings
              </p>
            </div>

            <div className="space-y-4">
              {/* Stealth Labels */}
              <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                <div className="flex items-center gap-3">
                  <Eye className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Stealth Labels
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      Hide sensitive document titles in UI (shows generic labels)
                    </div>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={securitySettings.stealth_labels}
                  onChange={(e) =>
                    updateSecuritySettings({ stealth_labels: e.target.checked })
                  }
                  className="w-5 h-5 rounded text-primary-600"
                />
              </div>

              {/* Decoy Mode */}
              <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                <div className="flex items-center gap-3">
                  <Shield className="w-5 h-5 text-amber-600 dark:text-amber-400" />
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Decoy Vault Enabled
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      Dual vault system with plausible deniability
                    </div>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={securitySettings.decoy_mode_enabled}
                  onChange={(e) =>
                    updateSecuritySettings({ decoy_mode_enabled: e.target.checked })
                  }
                  className="w-5 h-5 rounded text-primary-600"
                />
              </div>

              {/* Touch ID */}
              <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                <div className="flex items-center gap-3">
                  <Fingerprint className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Require Touch ID
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      Use biometric authentication to unlock documents
                    </div>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={securitySettings.require_touch_id}
                  onChange={(e) =>
                    updateSecuritySettings({ require_touch_id: e.target.checked })
                  }
                  className="w-5 h-5 rounded text-primary-600"
                />
              </div>

              {/* Auto-lock on exit */}
              <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                <div className="flex items-center gap-3">
                  <Lock className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Auto-lock on exit
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      Lock all documents when closing the app
                    </div>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={securitySettings.lock_on_exit}
                  onChange={(e) =>
                    updateSecuritySettings({ lock_on_exit: e.target.checked })
                  }
                  className="w-5 h-5 rounded text-primary-600"
                />
              </div>

              {/* Disable screenshots */}
              <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                <div className="flex items-center gap-3">
                  <Camera className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Disable screenshots
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      Prevent screenshots of sensitive content
                    </div>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={securitySettings.disable_screenshots}
                  onChange={(e) =>
                    updateSecuritySettings({ disable_screenshots: e.target.checked })
                  }
                  className="w-5 h-5 rounded text-primary-600"
                />
              </div>

              {/* Inactivity lock timer */}
              <div className="p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                  Inactivity Lock Timer
                </label>
                <select
                  value={securitySettings.inactivity_lock}
                  onChange={(e) =>
                    updateSecuritySettings({
                      inactivity_lock: e.target.value as 'instant' | '30s' | '1m' | '2m' | '3m' | '4m' | '5m',
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                >
                  <option value="instant">Instant</option>
                  <option value="30s">30 seconds</option>
                  <option value="1m">1 minute</option>
                  <option value="2m">2 minutes</option>
                  <option value="3m">3 minutes</option>
                  <option value="4m">4 minutes</option>
                  <option value="5m">5 minutes</option>
                </select>
              </div>

              {/* Biometric Credential Registration */}
              <div className="p-4 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                <div className="flex items-start gap-3 mb-3">
                  <Fingerprint className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5" />
                  <div className="flex-1">
                    <div className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-1">
                      Biometric Credential Setup
                    </div>
                    <div className="text-xs text-blue-700 dark:text-blue-300 mb-3">
                      {checkingBiometric ? (
                        'Checking biometric availability...'
                      ) : !biometricAvailable ? (
                        'Touch ID / Face ID not available on this device'
                      ) : biometricRegistered ? (
                        'Touch ID is registered and ready to use for vault access'
                      ) : (
                        'Register your biometric credential to unlock vault with Touch ID / Face ID'
                      )}
                    </div>

                    {!checkingBiometric && (
                      <div className="flex items-center gap-3">
                        {biometricAvailable ? (
                          biometricRegistered ? (
                            <div className="flex items-center gap-2 text-green-700 dark:text-green-400">
                              <CheckCircle className="w-4 h-4" />
                              <span className="text-xs font-medium">Registered</span>
                            </div>
                          ) : (
                            <button
                              onClick={handleRegisterBiometric}
                              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
                            >
                              <Fingerprint className="w-4 h-4" />
                              <span>Register Touch ID</span>
                            </button>
                          )
                        ) : (
                          <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                            <XCircle className="w-4 h-4" />
                            <span className="text-xs">Not available</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Updates Tab (formerly Cloud) */}
        {activeTab === 'updates' && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
                System Updates & Offline Operation
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                ElohimOS operates fully offline. No cloud sync or SaaS features.
              </p>
            </div>

            {/* Offline-Only Policy */}
            <div className="p-6 bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 border border-green-200 dark:border-green-800 rounded-xl">
              <div className="flex items-center gap-3 mb-3">
                <HardDrive className="w-6 h-6 text-green-600 dark:text-green-400" />
                <h4 className="font-semibold text-green-900 dark:text-green-100 text-lg">
                  Offline-First Design
                </h4>
              </div>
              <p className="text-sm text-green-700 dark:text-green-300 mb-3">
                ElohimOS is designed for complete offline operation. No cloud sync, no external dependencies, no tracking.
              </p>
              <ul className="text-xs text-green-700 dark:text-green-300 space-y-1">
                <li>• All data stored locally in ~/.elohimos_data/</li>
                <li>• Encrypted backups available via Settings → Danger Zone</li>
                <li>• P2P LAN sync available for team collaboration (local network only)</li>
                <li>• OS updates managed via system update mechanism</li>
              </ul>
            </div>

            {/* System Updates */}
            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
              <div className="flex items-center gap-3 mb-3">
                <Cloud className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                <h4 className="font-semibold text-blue-900 dark:text-blue-100">
                  OS Updates
                </h4>
              </div>
              <p className="text-sm text-blue-700 dark:text-blue-300 mb-2">
                ElohimOS receives updates via macOS system update mechanism.
              </p>
              <ul className="text-xs text-blue-700 dark:text-blue-300 space-y-1">
                <li>• Check for updates: System Settings → Software Update</li>
                <li>• Updates include security patches, bug fixes, and new features</li>
                <li>• All updates are cryptographically signed and verified</li>
                <li>• No telemetry or usage tracking</li>
              </ul>
            </div>

            <div className="space-y-4">
              {/* Network Policy */}
              <div className="p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    Network Policy
                  </div>
                  <span className="text-xs px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded">
                    Local Only
                  </span>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  No cloud sync. P2P LAN/mesh only. Updates via OS. All data local.
                </p>
              </div>

              {/* Data Storage Info */}
              <div className="p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
                  Local Data Directories
                </label>
                <div className="space-y-2 text-xs font-mono text-gray-600 dark:text-gray-400">
                  <div className="flex items-center gap-2 p-2 bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700">
                    <HardDrive className="w-4 h-4 flex-shrink-0" />
                    <div>
                      <div className="font-semibold text-gray-900 dark:text-gray-100">Databases</div>
                      <div>~/.elohimos_data/</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 p-2 bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700">
                    <HardDrive className="w-4 h-4 flex-shrink-0" />
                    <div>
                      <div className="font-semibold text-gray-900 dark:text-gray-100">Backups</div>
                      <div>~/.elohimos_backups/</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 p-2 bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700">
                    <HardDrive className="w-4 h-4 flex-shrink-0" />
                    <div>
                      <div className="font-semibold text-gray-900 dark:text-gray-100">Vault</div>
                      <div>~/.elohimos_data/vault/</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Privacy Tab */}
        {activeTab === 'privacy' && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
                Privacy & Data Control
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Manage your data and privacy settings
              </p>
            </div>

            <div className="space-y-4">
              {/* Stealth Mode */}
              <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                <div className="flex items-center gap-3">
                  <Eye className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Stealth Labels
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      Hide sensitive document titles in UI (shows generic labels)
                    </div>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={securitySettings.stealth_labels}
                  onChange={(e) => {
                    updateSecuritySettings({ stealth_labels: e.target.checked })
                    toast.success(
                      e.target.checked
                        ? 'Stealth labels enabled - Document titles will be hidden'
                        : 'Stealth labels disabled - Document titles will be shown'
                    )
                  }}
                  className="w-5 h-5 rounded text-primary-600"
                />
              </div>

              {/* Decoy Mode */}
              <div className="flex items-center justify-between p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
                <div className="flex items-center gap-3">
                  <Shield className="w-5 h-5 text-amber-600 dark:text-amber-400" />
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Decoy Vault Enabled
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      Dual vault system with plausible deniability
                    </div>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={securitySettings.decoy_mode_enabled}
                  onChange={(e) => {
                    updateSecuritySettings({ decoy_mode_enabled: e.target.checked })
                    toast.success(
                      e.target.checked
                        ? 'Decoy vault enabled - Use alternate password to access decoy vault'
                        : 'Decoy vault disabled - Only real vault is active'
                    )
                  }}
                  className="w-5 h-5 rounded text-amber-600"
                />
              </div>

              {/* Data Location */}
              <div className="p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                  Data Storage Location
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400 font-mono bg-white dark:bg-gray-800 p-2 rounded border border-gray-300 dark:border-gray-600">
                  ~/Library/Application Support/ElohimOS/.neutron_data
                </div>
              </div>

              {/* Export/Import */}
              <div className="space-y-2">
                <button
                  onClick={handleExportData}
                  className="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900/50 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <FileDown className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                    <div className="text-left">
                      <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        Export All Data
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        Download complete backup as ZIP
                      </div>
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-gray-400" />
                </button>

                <button
                  onClick={handleImportBackup}
                  className="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900/50 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <FileUp className="w-5 h-5 text-green-600 dark:text-green-400" />
                    <div className="text-left">
                      <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        Import Backup
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        Restore data from ZIP backup
                      </div>
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-gray-400" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Danger Zone Tab */}
        {activeTab === 'danger' && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-red-600 dark:text-red-400 mb-1">
                Danger Zone
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Irreversible actions - proceed with caution
              </p>
            </div>

            <div className="space-y-3">
              {/* Logout Button */}
              <div className="p-4 border-2 border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                <div className="flex items-start gap-3 mb-3">
                  <User className="w-5 h-5 text-gray-600 dark:text-gray-400 mt-0.5" />
                  <div className="flex-1">
                    <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-1">
                      Logout
                    </div>
                    <div className="text-xs text-gray-600 dark:text-gray-400 mb-3">
                      Sign out of your account and return to the login screen
                    </div>
                    <button
                      onClick={() => {
                        localStorage.removeItem('auth_token')
                        localStorage.removeItem('user')
                        window.location.reload()
                      }}
                      className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg text-sm font-medium transition-colors"
                    >
                      Logout
                    </button>
                  </div>
                </div>
              </div>
              {/* Reset User Identity */}
              <div className="p-4 border-2 border-orange-200 dark:border-orange-900 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                <div className="flex items-start gap-3 mb-3">
                  <RefreshCw className="w-5 h-5 text-orange-600 dark:text-orange-400 mt-0.5" />
                  <div className="flex-1">
                    <div className="text-sm font-semibold text-orange-900 dark:text-orange-100 mb-1">
                      Reset User Identity
                    </div>
                    <div className="text-xs text-orange-700 dark:text-orange-300 mb-3">
                      Generate new User ID. Your documents and data will be preserved.
                    </div>
                    <button
                      onClick={handleResetIdentity}
                      className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg text-sm font-medium transition-colors"
                    >
                      Reset Identity
                    </button>
                  </div>
                </div>
              </div>

              {/* Delete All Data */}
              <div className="p-4 border-2 border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-900/20 rounded-lg">
                <div className="flex items-start gap-3 mb-3">
                  <Trash2 className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5" />
                  <div className="flex-1">
                    <div className="text-sm font-semibold text-red-900 dark:text-red-100 mb-1">
                      Delete All Local Data
                    </div>
                    <div className="text-xs text-red-700 dark:text-red-300 mb-3">
                      Remove all documents, chats, and files. Settings will be preserved. Cannot
                      be undone.
                    </div>
                    <button
                      onClick={handleDeleteAllData}
                      className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors"
                    >
                      Delete All Data
                    </button>
                  </div>
                </div>
              </div>

              {/* Factory Reset */}
              <div className="p-4 border-2 border-red-300 dark:border-red-900 bg-red-100 dark:bg-red-950/40 rounded-lg">
                <div className="flex items-start gap-3 mb-3">
                  <AlertTriangle className="w-5 h-5 text-red-700 dark:text-red-400 mt-0.5" />
                  <div className="flex-1">
                    <div className="text-sm font-semibold text-red-950 dark:text-red-50 mb-1">
                      Factory Reset
                    </div>
                    <div className="text-xs text-red-800 dark:text-red-200 mb-3">
                      Complete wipe - deletes everything (data + settings + identity). Like a
                      fresh install. Cannot be undone.
                    </div>
                    <button
                      onClick={handleFactoryReset}
                      className="px-4 py-2 bg-red-700 hover:bg-red-800 text-white rounded-lg text-sm font-medium transition-colors"
                    >
                      Factory Reset
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
