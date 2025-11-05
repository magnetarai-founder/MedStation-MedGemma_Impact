/**
 * CodeView - Main code editing view with split panes
 *
 * Layout:
 * - Left Pane: File browser / Chat history
 * - Right Pane: Monaco editor / Chat pane
 */

import { useState } from 'react'
import { FolderTree, MessageSquare, FileCode } from 'lucide-react'
import { ResizableSidebar } from './ResizableSidebar'

export function CodeView() {
  const [leftView, setLeftView] = useState<'files' | 'chats'>('files')

  return (
    <ResizableSidebar
      initialWidth={280}
      minWidth={200}
      storageKey="ns.codeViewSidebarWidth"
      left={
        <div className="h-full flex flex-col bg-gray-50 dark:bg-gray-900">
          {/* Left Pane Header */}
          <div className="p-3 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-1">
              <button
                onClick={() => setLeftView('files')}
                className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-md transition-all ${
                  leftView === 'files'
                    ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 font-medium'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700/50'
                }`}
              >
                <FolderTree className="w-4 h-4" />
                <span>Files</span>
              </button>

              <button
                onClick={() => setLeftView('chats')}
                className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-md transition-all ${
                  leftView === 'chats'
                    ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 font-medium'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700/50'
                }`}
              >
                <MessageSquare className="w-4 h-4" />
                <span>Chats</span>
              </button>
            </div>
          </div>

          {/* Left Pane Content */}
          <div className="flex-1 overflow-auto">
            {leftView === 'files' && (
              <div className="p-4 space-y-2">
                <div className="text-center space-y-2 mt-20">
                  <FolderTree className="w-12 h-12 mx-auto text-gray-400 dark:text-gray-600" />
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    File browser
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-500">
                    Phase 2: Read-Only Files
                  </p>
                </div>
              </div>
            )}

            {leftView === 'chats' && (
              <div className="p-4 space-y-2">
                <div className="text-center space-y-2 mt-20">
                  <MessageSquare className="w-12 h-12 mx-auto text-gray-400 dark:text-gray-600" />
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Chat history
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-500">
                    Phase 4: Chat Integration
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      }
      right={
        <div className="h-full flex flex-col bg-gray-50 dark:bg-gray-900">
          {/* Right Pane - Monaco Editor Placeholder */}
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center space-y-4">
              <FileCode className="w-16 h-16 mx-auto text-gray-400 dark:text-gray-600" />
              <div className="space-y-2">
                <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
                  Monaco Editor
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  VS Code's editor component
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-500">
                  Phase 2: Read-Only File Viewing
                </p>
              </div>
            </div>
          </div>
        </div>
      }
    />
  )
}
