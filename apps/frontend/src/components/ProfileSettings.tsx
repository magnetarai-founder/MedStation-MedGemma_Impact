/**
 * Profile Settings Component
 *
 * Global user profile and settings - integrated into SettingsModal
 * Includes: Identity, Security, Cloud/SaaS, Privacy, Danger Zone
 */

import { useState, useEffect } from 'react'
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
} from 'lucide-react'
import { useUserStore } from '@/stores/userStore'
import { useDocsStore } from '@/stores/docsStore'
import toast from 'react-hot-toast'

type ProfileTab = 'identity' | 'security' | 'cloud' | 'privacy' | 'danger'
type LicenseType = 'none' | 'mission' | 'church' | 'business'

export function ProfileSettings() {
  const { user, fetchUser, updateUser, resetUser, isLoading } = useUserStore()
  const { securitySettings, updateSecuritySettings } = useDocsStore()

  // Debug logging
  console.log('ProfileSettings - user:', user)
  console.log('ProfileSettings - isLoading:', isLoading)

  const [activeTab, setActiveTab] = useState<ProfileTab>('identity')
  const [displayName, setDisplayName] = useState(user?.display_name || '')
  const [deviceName, setDeviceName] = useState(user?.device_name || '')
  const [avatarColor, setAvatarColor] = useState(user?.avatar_color || '#3b82f6')
  const [bio, setBio] = useState(user?.bio || '')
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [copiedUserId, setCopiedUserId] = useState(false)

  // Cloud/SaaS state
  const [licenseType, setLicenseType] = useState<LicenseType>('none')
  const [licenseKey, setLicenseKey] = useState('')

  // Auto-fetch user on mount if not loaded
  useEffect(() => {
    if (!user && !isLoading) {
      fetchUser()
    }
  }, [])

  // Update local state when user changes
  useEffect(() => {
    if (user) {
      setDisplayName(user.display_name || '')
      setDeviceName(user.device_name || '')
      setAvatarColor(user.avatar_color || '#3b82f6')
      setBio(user.bio || '')
    }
  }, [user])

  const handleSaveProfile = async () => {
    try {
      await updateUser({
        display_name: displayName,
        device_name: deviceName,
        avatar_color: avatarColor,
        bio: bio,
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

  const handleActivateLicense = () => {
    toast('Cloud activation - Coming soon')
  }

  const tabs = [
    { id: 'identity' as const, label: 'Identity', icon: User },
    { id: 'security' as const, label: 'Security', icon: Shield },
    { id: 'cloud' as const, label: 'Cloud & SaaS', icon: Cloud },
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
                  Unique identifier for P2P connections and cloud sync
                </p>
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
                  checked={securitySettings.auto_lock_on_exit}
                  onChange={(e) =>
                    updateSecuritySettings({ auto_lock_on_exit: e.target.checked })
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
                  value={securitySettings.inactivity_lock_minutes || 0}
                  onChange={(e) =>
                    updateSecuritySettings({
                      inactivity_lock_minutes: parseInt(e.target.value),
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                >
                  <option value={0}>Instant</option>
                  <option value={1}>1 minute</option>
                  <option value={5}>5 minutes</option>
                  <option value={15}>15 minutes</option>
                  <option value={30}>30 minutes</option>
                  <option value={-1}>Never</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* Cloud & SaaS Tab */}
        {activeTab === 'cloud' && (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
                Cloud Sync & SaaS Licensing
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Connect to cloud storage and manage your license
              </p>
            </div>

            {/* Coming Soon Banner */}
            <div className="p-6 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-200 dark:border-blue-800 rounded-xl">
              <div className="flex items-center gap-3 mb-3">
                <Cloud className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                <h4 className="font-semibold text-blue-900 dark:text-blue-100 text-lg">
                  Coming Soon
                </h4>
              </div>
              <p className="text-sm text-blue-700 dark:text-blue-300">
                Cloud sync and SaaS features are currently in development. Backup your data locally
                for now.
              </p>
            </div>

            {/* Pricing Model */}
            <div className="flex items-center gap-4 p-4 bg-white/50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2">
                <Heart className="w-5 h-5 text-red-500" />
                <div>
                  <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                    FREE for Missions & Churches
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400">
                    Unlimited storage, forever
                  </div>
                </div>
              </div>
              <div className="border-l border-gray-300 dark:border-gray-600 h-10"></div>
              <div className="flex items-center gap-2">
                <Building2 className="w-5 h-5 text-blue-500" />
                <div>
                  <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                    Paid for Businesses
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400">$49/user/month</div>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              {/* Connection Status */}
              <div className="p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    Connection Status
                  </div>
                  <span className="text-xs px-2 py-1 bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded">
                    Offline Only
                  </span>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Cloud sync is not yet available. All data is stored locally.
                </p>
              </div>

              {/* License Type Selector */}
              <div className="p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
                  License Type
                </label>
                <div className="space-y-2">
                  <label className="flex items-center justify-between p-3 border border-gray-300 dark:border-gray-600 rounded-lg cursor-pointer hover:bg-white dark:hover:bg-gray-800 transition-colors">
                    <div className="flex items-center gap-3">
                      <Heart className="w-4 h-4 text-red-500" />
                      <div>
                        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          Mission Organization
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          FREE - Unlimited storage
                        </div>
                      </div>
                    </div>
                    <input
                      type="radio"
                      name="license"
                      value="mission"
                      checked={licenseType === 'mission'}
                      onChange={(e) => setLicenseType(e.target.value as LicenseType)}
                      className="w-4 h-4 text-primary-600"
                    />
                  </label>

                  <label className="flex items-center justify-between p-3 border border-gray-300 dark:border-gray-600 rounded-lg cursor-pointer hover:bg-white dark:hover:bg-gray-800 transition-colors">
                    <div className="flex items-center gap-3">
                      <Church className="w-4 h-4 text-purple-500" />
                      <div>
                        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          Church/Ministry
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          FREE - Unlimited storage
                        </div>
                      </div>
                    </div>
                    <input
                      type="radio"
                      name="license"
                      value="church"
                      checked={licenseType === 'church'}
                      onChange={(e) => setLicenseType(e.target.value as LicenseType)}
                      className="w-4 h-4 text-primary-600"
                    />
                  </label>

                  <label className="flex items-center justify-between p-3 border border-gray-300 dark:border-gray-600 rounded-lg cursor-pointer hover:bg-white dark:hover:bg-gray-800 transition-colors">
                    <div className="flex items-center gap-3">
                      <Building2 className="w-4 h-4 text-blue-500" />
                      <div>
                        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          Business/Enterprise
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          $49/user/month
                        </div>
                      </div>
                    </div>
                    <input
                      type="radio"
                      name="license"
                      value="business"
                      checked={licenseType === 'business'}
                      onChange={(e) => setLicenseType(e.target.value as LicenseType)}
                      className="w-4 h-4 text-primary-600"
                    />
                  </label>
                </div>
              </div>

              {/* License Key */}
              <div className="p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                  License Key
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={licenseKey}
                    onChange={(e) => setLicenseKey(e.target.value)}
                    placeholder="XXXX-XXXX-XXXX-XXXX"
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 font-mono"
                  />
                  <button
                    onClick={handleActivateLicense}
                    className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors"
                  >
                    Activate
                  </button>
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
                  <Eye className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Stealth Mode Labels
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      Hide sensitive document titles in UI
                    </div>
                  </div>
                </div>
                <input
                  type="checkbox"
                  className="w-5 h-5 rounded text-primary-600"
                  onChange={() => toast('Stealth mode - Coming soon')}
                />
              </div>

              {/* Decoy Mode */}
              <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                <div className="flex items-center gap-3">
                  <Shield className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Decoy Mode
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      Show fake data when unlocking with alternate password
                    </div>
                  </div>
                </div>
                <input
                  type="checkbox"
                  className="w-5 h-5 rounded text-primary-600"
                  onChange={() => toast('Decoy mode - Coming soon')}
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
