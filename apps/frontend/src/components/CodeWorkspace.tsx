/**
 * Code Workspace - AI-powered code editing environment
 *
 * Features:
 * - File browser with tree view
 * - Monaco code editor
 * - AI chat for code assistance
 * - Terminal integration (via global button)
 */

import { useState } from 'react'
import { Code, FileText } from 'lucide-react'
import { CodeView } from './CodeView'

type WorkspaceView = 'editor' | 'admin'

export function CodeWorkspace() {
  const [activeView, setActiveView] = useState<WorkspaceView>('editor')

  return (
    <div className="h-full w-full flex flex-col">
      {/* Sub-navigation bar */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/30">
        {/* View Tabs */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => setActiveView('editor')}
            className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-md transition-all ${
              activeView === 'editor'
                ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 font-medium'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700/50'
            }`}
          >
            <Code className="w-4 h-4" />
            <span>Code</span>
          </button>

          <button
            onClick={() => setActiveView('admin')}
            className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-md transition-all ${
              activeView === 'admin'
                ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 font-medium'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700/50'
            }`}
          >
            <FileText className="w-4 h-4" />
            <span>Admin</span>
          </button>
        </div>
      </div>

      {/* Content area */}
      <div className="flex-1 min-h-0">
        {activeView === 'editor' && <CodeView />}

        {activeView === 'admin' && (
          <div className="h-full flex items-center justify-center bg-gray-50 dark:bg-gray-900">
            <div className="text-center space-y-4">
              <FileText className="w-16 h-16 mx-auto text-gray-400 dark:text-gray-600" />
              <div className="space-y-2">
                <h2 className="text-2xl font-semibold text-gray-800 dark:text-gray-200">
                  Code Admin
                </h2>
                <p className="text-gray-600 dark:text-gray-400 max-w-md">
                  Manage code workspaces, permissions, and integrations.
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-500">
                  Coming in Phase 9...
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
