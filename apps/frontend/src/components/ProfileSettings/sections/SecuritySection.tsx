/**
 * SecuritySection Component
 *
 * Security settings and biometric authentication
 */

import { Eye, Shield, Fingerprint, Lock, Camera, CheckCircle, XCircle } from 'lucide-react'
import { SectionHeader } from '../components/SectionHeader'
import { SettingToggle } from '../components/SettingToggle'
import type { SecuritySettings, BiometricState, BiometricHandlers } from '../types'

interface SecuritySectionProps {
  securitySettings: SecuritySettings
  updateSecuritySettings: (settings: Partial<SecuritySettings>) => void
  biometricState: BiometricState
  biometricHandlers: BiometricHandlers
}

export function SecuritySection({
  securitySettings,
  updateSecuritySettings,
  biometricState,
  biometricHandlers,
}: SecuritySectionProps) {
  return (
    <div className="space-y-6">
      <SectionHeader
        title="Security & Authentication"
        description="Configure Touch ID and document security settings"
      />

      <div className="space-y-4">
        {/* Stealth Labels */}
        <SettingToggle
          icon={Eye}
          label="Stealth Labels"
          description="Hide sensitive document titles in UI (shows generic labels)"
          checked={securitySettings.stealth_labels}
          onChange={(checked) => updateSecuritySettings({ stealth_labels: checked })}
        />

        {/* Decoy Mode */}
        <SettingToggle
          icon={Shield}
          label="Decoy Vault Enabled"
          description="Dual vault system with plausible deniability"
          checked={securitySettings.decoy_mode_enabled}
          onChange={(checked) => updateSecuritySettings({ decoy_mode_enabled: checked })}
        />

        {/* Touch ID */}
        <SettingToggle
          icon={Fingerprint}
          label="Require Touch ID"
          description="Use biometric authentication to unlock documents"
          checked={securitySettings.require_touch_id}
          onChange={(checked) => updateSecuritySettings({ require_touch_id: checked })}
        />

        {/* Auto-lock on exit */}
        <SettingToggle
          icon={Lock}
          label="Auto-lock on exit"
          description="Lock all documents when closing the app"
          checked={securitySettings.lock_on_exit}
          onChange={(checked) => updateSecuritySettings({ lock_on_exit: checked })}
        />

        {/* Disable screenshots */}
        <SettingToggle
          icon={Camera}
          label="Disable screenshots"
          description="Prevent screenshots of sensitive content"
          checked={securitySettings.disable_screenshots}
          onChange={(checked) => updateSecuritySettings({ disable_screenshots: checked })}
        />

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
                {biometricState.checkingBiometric ? (
                  'Checking biometric availability...'
                ) : !biometricState.biometricAvailable ? (
                  'Touch ID / Face ID not available on this device'
                ) : biometricState.biometricRegistered ? (
                  'Touch ID is registered and ready to use for vault access'
                ) : (
                  'Register your biometric credential to unlock vault with Touch ID / Face ID'
                )}
              </div>

              {!biometricState.checkingBiometric && (
                <div className="flex items-center gap-3">
                  {biometricState.biometricAvailable ? (
                    biometricState.biometricRegistered ? (
                      <div className="flex items-center gap-2 text-green-700 dark:text-green-400">
                        <CheckCircle className="w-4 h-4" />
                        <span className="text-xs font-medium">Registered</span>
                      </div>
                    ) : (
                      <button
                        onClick={biometricHandlers.handleRegisterBiometric}
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
  )
}
