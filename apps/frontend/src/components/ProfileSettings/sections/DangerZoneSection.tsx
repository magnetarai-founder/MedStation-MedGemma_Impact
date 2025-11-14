/**
 * DangerZoneSection Component
 *
 * Destructive actions and account management
 */

import { User, RefreshCw, Trash2, AlertTriangle } from 'lucide-react'
import { SectionHeader } from '../components/SectionHeader'
import type { DangerHandlers } from '../types'

interface DangerZoneSectionProps {
  dangerHandlers: DangerHandlers
}

export function DangerZoneSection({ dangerHandlers }: DangerZoneSectionProps) {
  return (
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
                onClick={dangerHandlers.handleLogout}
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
                onClick={dangerHandlers.handleResetIdentity}
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
                onClick={dangerHandlers.handleDeleteAllData}
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
                onClick={dangerHandlers.handleFactoryReset}
                className="px-4 py-2 bg-red-700 hover:bg-red-800 text-white rounded-lg text-sm font-medium transition-colors"
              >
                Factory Reset
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
