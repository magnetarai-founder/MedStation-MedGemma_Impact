/**
 * Team Workspace - Container for Chat and Docs & Sheets
 *
 * Provides sub-navigation between:
 * - Team Chat (P2P collaboration)
 * - Docs & Sheets (Documents, Spreadsheets, Insights Lab)
 */

import { useState } from 'react'
import { useDocsStore } from '@/stores/docsStore'
import { useTeamStore } from '@/stores/teamStore'
import { usePermissions } from '@/hooks/usePermissions'
import { TeamChat } from './TeamChat'
import { DocsWorkspace } from './DocsWorkspace'
import { VaultSetup } from './VaultSetup'
import { VaultWorkspace } from './VaultWorkspace'
import { NetworkSelector } from './NetworkSelector'
import { MessageSquare, FileText, Lock } from 'lucide-react'

export function TeamWorkspace() {
  const { workspaceView, setWorkspaceView, vaultSetupComplete, vaultUnlocked } = useDocsStore()
  const { networkMode, setNetworkMode } = useTeamStore()
  const permissions = usePermissions()
  const [showVaultSetup, setShowVaultSetup] = useState(false)

  const handleVaultClick = () => {
    if (!vaultSetupComplete) {
      setShowVaultSetup(true)
    } else {
      setWorkspaceView('vault')
    }
  }

  return (
    <div className="h-full w-full flex flex-col">
      {/* Sub-navigation bar */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/30">
        {/* Network Selector - Globe Icon */}
        <NetworkSelector mode={networkMode} onModeChange={setNetworkMode} />

        {/* Vertical Divider */}
        <div className="h-6 w-px bg-gray-300 dark:bg-gray-600"></div>

        {/* View Tabs */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => setWorkspaceView('chat')}
            className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-md transition-all ${
              workspaceView === 'chat'
                ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 font-medium'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700/50'
            }`}
          >
            <MessageSquare className="w-4 h-4" />
            <span>Chat</span>
          </button>

          {/* Docs Tab - Members and above only */}
          {permissions.canAccessDocuments && (
            <button
              onClick={() => setWorkspaceView('docs')}
              className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-md transition-all ${
                workspaceView === 'docs'
                  ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 font-medium'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700/50'
              }`}
            >
              <FileText className="w-4 h-4" />
              <span>Docs</span>
            </button>
          )}

          {/* Vertical Divider - only show if Docs or Vault are visible */}
          {(permissions.canAccessDocuments || permissions.canAccessVault) && (
            <div className="h-6 w-px bg-gray-300 dark:bg-gray-600 mx-2"></div>
          )}

          {/* Vault Tab - Members and above only */}
          {permissions.canAccessVault && (
            <button
              onClick={handleVaultClick}
              className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-md transition-all ${
                workspaceView === 'vault'
                  ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 font-medium'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-amber-50 dark:hover:bg-amber-900/20'
              }`}
            >
              <Lock className="w-4 h-4" />
              <span>Vault</span>
            </button>
          )}
        </div>
      </div>

      {/* Content area */}
      <div className="flex-1 min-h-0">
        {workspaceView === 'chat' && <TeamChat mode={networkMode} />}
        {workspaceView === 'docs' && <DocsWorkspace />}
        {workspaceView === 'vault' && <VaultWorkspace />}
      </div>

      {/* Vault Setup Modal */}
      {showVaultSetup && (
        <VaultSetup
          onComplete={() => {
            setShowVaultSetup(false)
            setWorkspaceView('vault')
          }}
          onCancel={() => {
            setShowVaultSetup(false)
          }}
        />
      )}
    </div>
  )
}
