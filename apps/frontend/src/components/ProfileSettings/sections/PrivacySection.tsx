/**
 * PrivacySection Component
 *
 * Privacy settings and data control
 */

import { Eye, Shield, FileDown, FileUp, ChevronRight } from 'lucide-react'
import toast from 'react-hot-toast'
import { SectionHeader } from '../components/SectionHeader'
import type { SecuritySettings, PrivacyHandlers } from '../types'

interface PrivacySectionProps {
  securitySettings: SecuritySettings
  updateSecuritySettings: (settings: Partial<SecuritySettings>) => void
  privacyHandlers: PrivacyHandlers
}

export function PrivacySection({
  securitySettings,
  updateSecuritySettings,
  privacyHandlers,
}: PrivacySectionProps) {
  return (
    <div className="space-y-6">
      <SectionHeader
        title="Privacy & Data Control"
        description="Manage your data and privacy settings"
      />

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
            onClick={privacyHandlers.handleExportData}
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
            onClick={privacyHandlers.handleImportBackup}
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
  )
}
