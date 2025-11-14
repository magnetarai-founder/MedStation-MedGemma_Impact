/**
 * UpdatesSection Component
 *
 * System updates and offline operation information
 */

import { HardDrive, Cloud } from 'lucide-react'
import { SectionHeader } from '../components/SectionHeader'
import { InfoCard } from '../components/InfoCard'

export function UpdatesSection() {
  return (
    <div className="space-y-6">
      <SectionHeader
        title="System Updates & Offline Operation"
        description="ElohimOS operates fully offline. No cloud sync or SaaS features."
      />

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
  )
}
