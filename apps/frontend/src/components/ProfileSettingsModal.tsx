/**
 * User Profile & Global Settings
 *
 * Global user settings including:
 * - User identity & profile
 * - Security & biometric authentication
 * - Cloud sync & SaaS licensing (placeholders)
 * - Privacy controls
 * - Account management
 */

import { useState, useEffect } from 'react'
import {
  X, User, Shield, Cloud, Lock, Palette, AlertTriangle,
  Save, Fingerprint, Key, Globe, Building2, Church, Heart,
  Download, Upload, Trash2, RotateCcw, Check, Loader2
} from 'lucide-react'
import { useUserStore } from '@/stores/userStore'
import { useDocsStore } from '@/stores/docsStore'
import toast from 'react-hot-toast'

interface ProfileSettingsModalProps {
  isOpen: boolean
  onClose: () => void
}

type ProfileTab = 'identity' | 'security' | 'cloud' | 'privacy' | 'danger'
type LicenseType = 'none' | 'mission' | 'church' | 'nonprofit' | 'individual' | 'business'

export function ProfileSettingsModal({ isOpen, onClose }: ProfileSettingsModalProps) {
  const [activeTab, setActiveTab] = useState<ProfileTab>('identity')
  const { user, updateUser, resetUser, isLoading } = useUserStore()
  const { securitySettings, updateSecuritySettings } = useDocsStore()

  // Form state
  const [displayName, setDisplayName] = useState(user?.display_name || '')
  const [deviceName, setDeviceName] = useState(user?.device_name || '')
  const [avatarColor, setAvatarColor] = useState(user?.avatar_color || '#3b82f6')
  const [bio, setBio] = useState(user?.bio || '')
  const [hasChanges, setHasChanges] = useState(false)

  // Cloud/SaaS state (placeholders)
  const [isCloudConnected, setIsCloudConnected] = useState(false)
  const [licenseType, setLicenseType] = useState<LicenseType>('none')
  const [licenseKey, setLicenseKey] = useState('')

  // Update form when user loads
  useEffect(() => {
    if (user) {
      setDisplayName(user.display_name)
      setDeviceName(user.device_name)
      setAvatarColor(user.avatar_color || '#3b82f6')
      setBio(user.bio || '')
    }
  }, [user])

  // Track changes
  useEffect(() => {
    if (!user) return
    const changed =
      displayName !== user.display_name ||
      deviceName !== user.device_name ||
      avatarColor !== user.avatar_color ||
      bio !== (user.bio || '')
    setHasChanges(changed)
  }, [displayName, deviceName, avatarColor, bio, user])

  // Handle ESC key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose()
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])

  // Save profile changes
  const handleSaveProfile = async () => {
    try {
      await updateUser({
        display_name: displayName,
        device_name: deviceName,
        avatar_color: avatarColor,
        bio: bio || undefined,
      })
      toast.success('Profile updated successfully!')
      setHasChanges(false)
    } catch (error) {
      toast.error('Failed to update profile')
    }
  }

  // Reset user identity
  const handleResetIdentity = async () => {
    if (!confirm('Reset your user identity? This will create a new User ID but keep your data.')) {
      return
    }
    try {
      await resetUser()
      toast.success('User identity reset successfully!')
    } catch (error) {
      toast.error('Failed to reset identity')
    }
  }

  // Cloud placeholder actions
  const handleConnectCloud = () => {
    toast.error('Cloud sync coming soon! Stay tuned for updates.', { duration: 4000 })
  }

  const handleActivateLicense = () => {
    if (!licenseKey.trim()) {
      toast.error('Please enter a license key')
      return
    }
    toast.error('License activation coming soon!', { duration: 4000 })
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />

      {/* Modal */}
      <div className="relative w-full max-w-5xl max-h-[90vh] bg-white dark:bg-gray-900 rounded-2xl shadow-2xl flex overflow-hidden">
        {/* Sidebar */}
        <div className="w-64 bg-gray-50 dark:bg-gray-800/50 border-r border-gray-200 dark:border-gray-700 p-4">
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
              Profile & Settings
            </h2>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Manage your account
            </p>
          </div>

          <nav className="space-y-1">
            <button
              onClick={() => setActiveTab('identity')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'identity'
                  ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50'
              }`}
            >
              <User className="w-4 h-4" />
              User Identity
            </button>

            <button
              onClick={() => setActiveTab('security')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'security'
                  ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50'
              }`}
            >
              <Shield className="w-4 h-4" />
              Security & Auth
            </button>

            <button
              onClick={() => setActiveTab('cloud')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'cloud'
                  ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50'
              }`}
            >
              <Cloud className="w-4 h-4" />
              <div className="flex-1 text-left">
                Cloud & SaaS
              </div>
              <span className="text-[10px] px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded font-semibold">
                NEW
              </span>
            </button>

            <button
              onClick={() => setActiveTab('privacy')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'privacy'
                  ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50'
              }`}
            >
              <Lock className="w-4 h-4" />
              Privacy & Data
            </button>

            <button
              onClick={() => setActiveTab('danger')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'danger'
                  ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50'
              }`}
            >
              <AlertTriangle className="w-4 h-4" />
              Danger Zone
            </button>
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-3">
              {activeTab === 'identity' && <User className="w-5 h-5 text-primary-600" />}
              {activeTab === 'security' && <Shield className="w-5 h-5 text-primary-600" />}
              {activeTab === 'cloud' && <Cloud className="w-5 h-5 text-primary-600" />}
              {activeTab === 'privacy' && <Lock className="w-5 h-5 text-primary-600" />}
              {activeTab === 'danger' && <AlertTriangle className="w-5 h-5 text-red-600" />}
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {activeTab === 'identity' && 'User Identity'}
                {activeTab === 'security' && 'Security & Authentication'}
                {activeTab === 'cloud' && 'Cloud Sync & SaaS'}
                {activeTab === 'privacy' && 'Privacy & Data Control'}
                {activeTab === 'danger' && 'Danger Zone'}
              </h3>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>

          {/* Scrollable Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {/* USER IDENTITY TAB */}
            {activeTab === 'identity' && (
              <div className="max-w-2xl space-y-6">
                {/* Display Name */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Display Name
                  </label>
                  <input
                    type="text"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    className="w-full px-4 py-2.5 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-gray-900 dark:text-gray-100"
                    placeholder="Field Worker"
                  />
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    Your name as it appears to other users in team collaboration
                  </p>
                </div>

                {/* Device Name */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Device Name
                  </label>
                  <input
                    type="text"
                    value={deviceName}
                    onChange={(e) => setDeviceName(e.target.value)}
                    className="w-full px-4 py-2.5 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-gray-900 dark:text-gray-100"
                    placeholder="Mac-1251.lan"
                  />
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    Identifies this device in mesh networks
                  </p>
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
                      onChange={(e) => setAvatarColor(e.target.value)}
                      className="h-12 w-20 rounded-lg cursor-pointer border border-gray-300 dark:border-gray-600"
                    />
                    <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                      <Palette className="w-4 h-4" />
                      {avatarColor}
                    </div>
                  </div>
                </div>

                {/* Bio */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Bio <span className="text-gray-400">(optional)</span>
                  </label>
                  <textarea
                    value={bio}
                    onChange={(e) => setBio(e.target.value)}
                    rows={3}
                    className="w-full px-4 py-2.5 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-gray-900 dark:text-gray-100 resize-none"
                    placeholder="Serving in Kenya..."
                  />
                </div>

                {/* User ID (read-only) */}
                <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    User ID <span className="text-gray-400">(read-only)</span>
                  </label>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 px-4 py-2.5 bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-xs text-gray-600 dark:text-gray-400 font-mono">
                      {user?.user_id || 'Loading...'}
                    </code>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(user?.user_id || '')
                        toast.success('User ID copied!')
                      }}
                      className="px-3 py-2.5 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 border border-gray-200 dark:border-gray-600 rounded-lg text-sm transition-colors"
                    >
                      Copy
                    </button>
                  </div>
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    Share this with support if you need help
                  </p>
                </div>

                {/* Save Button */}
                {hasChanges && (
                  <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                    <button
                      onClick={() => {
                        if (user) {
                          setDisplayName(user.display_name)
                          setDeviceName(user.device_name)
                          setAvatarColor(user.avatar_color || '#3b82f6')
                          setBio(user.bio || '')
                        }
                      }}
                      className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSaveProfile}
                      disabled={isLoading}
                      className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-400 text-white rounded-lg text-sm font-medium transition-colors"
                    >
                      {isLoading ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Saving...
                        </>
                      ) : (
                        <>
                          <Save className="w-4 h-4" />
                          Save Changes
                        </>
                      )}
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* SECURITY & AUTHENTICATION TAB */}
            {activeTab === 'security' && (
              <div className="max-w-2xl space-y-6">
                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <Fingerprint className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5" />
                    <div className="flex-1">
                      <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-1">
                        Biometric Authentication
                      </h4>
                      <p className="text-xs text-blue-700 dark:text-blue-300">
                        Touch ID/Face ID protects your locked documents with device-level security
                      </p>
                    </div>
                  </div>
                </div>

                {/* Touch ID Toggle */}
                <div className="flex items-center justify-between py-3">
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Require Touch ID for Locked Documents
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      Prompt for biometric authentication before unlocking
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={securitySettings.require_touch_id}
                      onChange={(e) => updateSecuritySettings({ require_touch_id: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
                  </label>
                </div>

                {/* Auto-lock */}
                <div className="flex items-center justify-between py-3">
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Auto-lock on Exit
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      Automatically lock insights when closing the app
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={securitySettings.lock_on_exit}
                      onChange={(e) => updateSecuritySettings({ lock_on_exit: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
                  </label>
                </div>

                {/* Disable Screenshots */}
                <div className="flex items-center justify-between py-3">
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Disable Screenshots (Insights)
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      Prevent screenshots of private insights
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={securitySettings.disable_screenshots}
                      onChange={(e) => updateSecuritySettings({ disable_screenshots: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
                  </label>
                </div>

                {/* Inactivity Lock */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Inactivity Lock Timer
                  </label>
                  <select
                    value={securitySettings.inactivity_lock}
                    onChange={(e) => updateSecuritySettings({ inactivity_lock: e.target.value as any })}
                    className="w-full px-4 py-2.5 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-gray-900 dark:text-gray-100"
                  >
                    <option value="instant">Instant</option>
                    <option value="30s">30 seconds</option>
                    <option value="1m">1 minute</option>
                    <option value="2m">2 minutes</option>
                    <option value="3m">3 minutes</option>
                    <option value="5m">5 minutes</option>
                  </select>
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    Automatically lock insights after this period of inactivity
                  </p>
                </div>
              </div>
            )}

            {/* CLOUD & SAAS TAB */}
            {activeTab === 'cloud' && (
              <div className="max-w-3xl space-y-6">
                {/* Coming Soon Banner */}
                <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 border-2 border-blue-200 dark:border-blue-800 rounded-xl p-6">
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-12 h-12 bg-blue-100 dark:bg-blue-900/40 rounded-full flex items-center justify-center">
                      <Cloud className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div className="flex-1">
                      <h4 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                        Cloud Sync & Backup
                      </h4>
                      <p className="text-sm text-gray-700 dark:text-gray-300 mb-4">
                        ElohimOS is offline-first by design. Optionally sync to cloud for backup, team collaboration, and cross-device access.
                      </p>
                      <div className="flex items-center gap-4 p-4 bg-white/50 dark:bg-gray-800/50 rounded-lg border border-blue-200 dark:border-blue-700">
                        <div className="flex items-center gap-2">
                          <Heart className="w-5 h-5 text-red-500" />
                          <div>
                            <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">FREE for Missions & Churches</div>
                            <div className="text-xs text-gray-600 dark:text-gray-400">Unlimited storage, forever</div>
                          </div>
                        </div>
                        <div className="border-l border-gray-300 dark:border-gray-600 h-10"></div>
                        <div className="flex items-center gap-2">
                          <Building2 className="w-5 h-5 text-blue-500" />
                          <div>
                            <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">Paid for Businesses</div>
                            <div className="text-xs text-gray-600 dark:text-gray-400">$49/user/month</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Status */}
                <div className="flex items-center gap-3 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <div className="flex-shrink-0 w-10 h-10 bg-gray-200 dark:bg-gray-700 rounded-full flex items-center justify-center">
                    <Globe className="w-5 h-5 text-gray-400" />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Status: Offline Only
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      No cloud account connected
                    </div>
                  </div>
                  <button
                    onClick={handleConnectCloud}
                    className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    Connect Cloud
                  </button>
                </div>

                {/* License Type Selector */}
                <div>
                  <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
                    Select Your Organization Type
                  </h4>
                  <div className="space-y-2">
                    <label className="flex items-center gap-3 p-3 border-2 border-gray-200 dark:border-gray-700 rounded-lg cursor-pointer hover:border-primary-300 dark:hover:border-primary-600 transition-colors">
                      <input
                        type="radio"
                        name="license"
                        value="mission"
                        checked={licenseType === 'mission'}
                        onChange={(e) => setLicenseType(e.target.value as LicenseType)}
                        className="w-4 h-4 text-primary-600"
                      />
                      <Heart className="w-5 h-5 text-red-500" />
                      <div className="flex-1">
                        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">Mission Organization</div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">FREE - Verification required</div>
                      </div>
                    </label>

                    <label className="flex items-center gap-3 p-3 border-2 border-gray-200 dark:border-gray-700 rounded-lg cursor-pointer hover:border-primary-300 dark:hover:border-primary-600 transition-colors">
                      <input
                        type="radio"
                        name="license"
                        value="church"
                        checked={licenseType === 'church'}
                        onChange={(e) => setLicenseType(e.target.value as LicenseType)}
                        className="w-4 h-4 text-primary-600"
                      />
                      <Church className="w-5 h-5 text-blue-500" />
                      <div className="flex-1">
                        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">Church / Ministry</div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">FREE - Verification required</div>
                      </div>
                    </label>

                    <label className="flex items-center gap-3 p-3 border-2 border-gray-200 dark:border-gray-700 rounded-lg cursor-pointer hover:border-primary-300 dark:hover:border-primary-600 transition-colors">
                      <input
                        type="radio"
                        name="license"
                        value="business"
                        checked={licenseType === 'business'}
                        onChange={(e) => setLicenseType(e.target.value as LicenseType)}
                        className="w-4 h-4 text-primary-600"
                      />
                      <Building2 className="w-5 h-5 text-blue-600" />
                      <div className="flex-1">
                        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">Business / Enterprise</div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">$49/user/month</div>
                      </div>
                    </label>
                  </div>
                </div>

                {/* License Key */}
                <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                  <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
                    Have a License Key?
                  </h4>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={licenseKey}
                      onChange={(e) => setLicenseKey(e.target.value.toUpperCase())}
                      placeholder="OMNI-XXXX-XXXX-XXXX"
                      className="flex-1 px-4 py-2.5 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-gray-900 dark:text-gray-100 font-mono text-sm"
                    />
                    <button
                      onClick={handleActivateLicense}
                      className="px-4 py-2.5 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 border border-gray-200 dark:border-gray-600 rounded-lg text-sm font-medium transition-colors"
                    >
                      Activate
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* PRIVACY TAB */}
            {activeTab === 'privacy' && (
              <div className="max-w-2xl space-y-6">
                {/* Stealth Mode */}
                <div className="flex items-center justify-between py-3">
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Stealth Mode Labels
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      Hide "ElohimOS" branding in UI (use generic labels)
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={securitySettings.stealth_labels}
                      onChange={(e) => updateSecuritySettings({ stealth_labels: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
                  </label>
                </div>

                {/* Decoy Mode */}
                <div className="flex items-center justify-between py-3">
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Decoy Mode
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      Show fake login screen on launch (for security)
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={securitySettings.decoy_mode_enabled}
                      onChange={(e) => updateSecuritySettings({ decoy_mode_enabled: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
                  </label>
                </div>

                {/* Data Location */}
                <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                  <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
                    Data Storage Locations
                  </h4>
                  <div className="space-y-2 text-xs">
                    <div className="flex items-start gap-2">
                      <span className="text-gray-500 dark:text-gray-400">Local:</span>
                      <code className="flex-1 px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded font-mono text-gray-700 dark:text-gray-300">
                        .neutron_data/
                      </code>
                    </div>
                    <div className="flex items-start gap-2">
                      <span className="text-gray-500 dark:text-gray-400">Cloud:</span>
                      <span className="text-gray-400">Not connected</span>
                    </div>
                  </div>
                </div>

                {/* Export/Import */}
                <div className="flex gap-3">
                  <button className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-700 rounded-lg text-sm font-medium transition-colors">
                    <Download className="w-4 h-4" />
                    Export All Data
                  </button>
                  <button className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-700 rounded-lg text-sm font-medium transition-colors">
                    <Upload className="w-4 h-4" />
                    Import Backup
                  </button>
                </div>
              </div>
            )}

            {/* DANGER ZONE TAB */}
            {activeTab === 'danger' && (
              <div className="max-w-2xl space-y-4">
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5" />
                    <div>
                      <h4 className="text-sm font-semibold text-red-900 dark:text-red-100 mb-1">
                        Warning: Irreversible Actions
                      </h4>
                      <p className="text-xs text-red-700 dark:text-red-300">
                        These actions cannot be undone. Proceed with caution.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Reset Identity */}
                <div className="p-4 border-2 border-gray-200 dark:border-gray-700 rounded-lg">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                      <RotateCcw className="w-5 h-5 text-gray-600 dark:text-gray-400 mt-0.5" />
                      <div>
                        <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-1">
                          Reset User Identity
                        </h4>
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          Create a new User ID. Your data will be preserved but you'll get a new identity.
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={handleResetIdentity}
                      className="flex-shrink-0 px-4 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-sm font-medium transition-colors"
                    >
                      Reset
                    </button>
                  </div>
                </div>

                {/* Delete All Data */}
                <div className="p-4 border-2 border-red-200 dark:border-red-800 rounded-lg">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                      <Trash2 className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5" />
                      <div>
                        <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-1">
                          Delete All Local Data
                        </h4>
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          Remove all documents, insights, chat history, and code files. Settings will be preserved.
                        </p>
                      </div>
                    </div>
                    <button className="flex-shrink-0 px-4 py-2 bg-red-100 dark:bg-red-900/30 hover:bg-red-200 dark:hover:bg-red-900/50 border border-red-300 dark:border-red-700 text-red-700 dark:text-red-400 rounded-lg text-sm font-medium transition-colors">
                      Delete
                    </button>
                  </div>
                </div>

                {/* Factory Reset */}
                <div className="p-4 border-2 border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/10 rounded-lg">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                      <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5" />
                      <div>
                        <h4 className="text-sm font-semibold text-red-900 dark:text-red-100 mb-1">
                          Factory Reset
                        </h4>
                        <p className="text-xs text-red-700 dark:text-red-300">
                          Complete wipe - removes everything including settings. Cannot be undone!
                        </p>
                      </div>
                    </div>
                    <button className="flex-shrink-0 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors">
                      Factory Reset
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
