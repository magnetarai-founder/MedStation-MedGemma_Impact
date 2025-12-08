import React, { Suspense } from 'react'
import { Toaster } from 'react-hot-toast'
import { FileUpload } from '../FileUpload'
import { SidebarTabs } from '../SidebarTabs'
import { Header } from '../Header'
import { ResizableSidebar } from '../ResizableSidebar'
import { NavigationRail } from '../NavigationRail'
import { ClearWorkspaceDialog } from '../ClearWorkspaceDialog'
import { OfflineIndicator } from '../OfflineIndicator'
import { FolderOpen, Clock, FileJson } from 'lucide-react'
import { lazyNamed } from '@/utils/lazyWithRetry'
import * as settingsApi from '@/lib/settingsApi'

// Lazy load heavy components for code splitting with retry logic
const ChatSidebar = lazyNamed(() => import('../ChatSidebar'), 'ChatSidebar')
const ChatWindow = lazyNamed(() => import('../ChatWindow'), 'ChatWindow')
const TeamWorkspace = lazyNamed(() => import('../TeamWorkspace'), 'TeamWorkspace')
const AdminPage = lazyNamed(() => import('@/pages/AdminPage'), 'default')
const KanbanWorkspace = lazyNamed(() => import('@/pages/KanbanWorkspace'), 'default')

// Lazy load modals (only loaded when opened) with retry logic
const SettingsModal = lazyNamed(() => import('../SettingsModal'), 'SettingsModal')
const LibraryModal = lazyNamed(() => import('../LibraryModal'), 'LibraryModal')
const JsonConverterModal = lazyNamed(() => import('../JsonConverterModal'), 'JsonConverterModal')
const QueryHistoryModal = lazyNamed(() => import('../QueryHistoryModal'), 'QueryHistoryModal')

// Loading spinner component for Suspense fallbacks
const LoadingSpinner = () => (
  <div className="h-full w-full flex items-center justify-center">
    <div className="relative w-12 h-12">
      <div className="absolute inset-0 bg-gradient-to-br from-primary-500 to-primary-700 rounded-full animate-pulse"></div>
      <div className="absolute inset-2 bg-gradient-to-br from-blue-300 to-primary-400 rounded-full"></div>
    </div>
  </div>
)

interface AppShellProps {
  activeTab: string
  onTabChange: (tab: string) => void
  // Modal state
  isSettingsOpen: boolean
  setIsSettingsOpen: (open: boolean) => void
  isLibraryOpen: boolean
  setIsLibraryOpen: (open: boolean) => void
  isJsonConverterOpen: boolean
  setIsJsonConverterOpen: (open: boolean) => void
  isQueryHistoryOpen: boolean
  setIsQueryHistoryOpen: (open: boolean) => void
  // File and query handling
  onLoadQuery: (query: settingsApi.SavedQuery) => void
  // Query history specific
  onRunQuery: (query: string) => void
}

export function AppShell(props: AppShellProps) {
  const {
    activeTab,
    onTabChange,
    isSettingsOpen,
    setIsSettingsOpen,
    isLibraryOpen,
    setIsLibraryOpen,
    isJsonConverterOpen,
    setIsJsonConverterOpen,
    isQueryHistoryOpen,
    setIsQueryHistoryOpen,
    onLoadQuery,
    onRunQuery,
  } = props

  return (
    <div className="h-screen flex flex-col">
      <Header />

      <div className="flex-1 flex overflow-hidden min-h-0">
        <NavigationRail
          activeTab={activeTab}
          onTabChange={onTabChange}
          onOpenSettings={() => setIsSettingsOpen(true)}
        />

        <div className="flex-1 flex flex-col min-h-0 min-w-0 relative">
          {/* Team Workspace Tab */}
          <div
            className="absolute inset-0 flex"
            style={{
              display: activeTab === 'team' ? 'flex' : 'none'
            }}
          >
            <Suspense fallback={<LoadingSpinner />}>
              <TeamWorkspace />
            </Suspense>
          </div>

          {/* AI Chat Tab */}
          <div
            className="absolute inset-0 flex"
            style={{
              display: activeTab === 'chat' ? 'flex' : 'none'
            }}
          >
            <Suspense fallback={<LoadingSpinner />}>
              <ResizableSidebar
                initialWidth={320}
                minWidth={280}
                storageKey="ns.chatSidebarWidth"
                left={<ChatSidebar />}
                right={<ChatWindow />}
              />
            </Suspense>
          </div>

          {/* Database Tab */}
          <div
            className="absolute inset-0 flex"
            style={{
              display: activeTab === 'database' ? 'flex' : 'none'
            }}
          >
            <ResizableSidebar
              initialWidth={320}
              minWidth={320}
              storageKey="ns.editorSidebarWidth"
              left={
                <div className="h-full flex flex-col">
                  <div className="p-4 pb-3 border-b border-gray-200 dark:border-gray-700">
                    <FileUpload />
                  </div>

                  {/* Icon Row - Library, Query History, JSON */}
                  <div className="flex items-center justify-center gap-2 py-2 border-b border-gray-200 dark:border-gray-700">
                    <button
                      onClick={() => setIsLibraryOpen(true)}
                      className="p-2 hover:bg-white/60 dark:hover:bg-gray-700/60 rounded-lg transition-all text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400"
                      title="Query Library"
                    >
                      <FolderOpen size={18} />
                    </button>
                    <button
                      onClick={() => setIsQueryHistoryOpen(true)}
                      className="p-2 hover:bg-white/60 dark:hover:bg-gray-700/60 rounded-lg transition-all text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400"
                      title="Query History"
                    >
                      <Clock size={18} />
                    </button>
                    <button
                      onClick={() => setIsJsonConverterOpen(true)}
                      className="p-2 hover:bg-white/60 dark:hover:bg-gray-700/60 rounded-lg transition-all text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400"
                      title="JSON Converter"
                    >
                      <FileJson size={18} />
                    </button>
                  </div>

                  <div className="flex-1 overflow-hidden">
                    <SidebarTabs />
                  </div>
                </div>
              }
              right={<ResizablePanels />}
            />
          </div>

          {/* Admin Tab */}
          <div
            className="absolute inset-0 flex"
            style={{
              display: activeTab === 'admin' ? 'flex' : 'none'
            }}
          >
            <Suspense fallback={<LoadingSpinner />}>
              <AdminPage />
            </Suspense>
          </div>

          {/* Kanban Tab */}
          <div
            className="absolute inset-0 flex"
            style={{
              display: activeTab === 'kanban' ? 'flex' : 'none'
            }}
          >
            <Suspense fallback={<LoadingSpinner />}>
              <KanbanWorkspace />
            </Suspense>
          </div>

        </div>
      </div>

      {/* Modals */}
      <Suspense fallback={null}>
        {isLibraryOpen && (
          <LibraryModal
            isOpen={isLibraryOpen}
            onClose={() => {
              setIsLibraryOpen(false)
            }}
            initialCodeData={null}
            onLoadQuery={onLoadQuery}
          />
        )}
      </Suspense>
      <Suspense fallback={null}>
        {isQueryHistoryOpen && (
          <QueryHistoryModal
            isOpen={isQueryHistoryOpen}
            onClose={() => setIsQueryHistoryOpen(false)}
            onRunQuery={onRunQuery}
          />
        )}
      </Suspense>
      <Suspense fallback={null}>
        {isSettingsOpen && (
          <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} activeNavTab={activeTab} />
        )}
      </Suspense>
      <Suspense fallback={null}>
        {isJsonConverterOpen && (
          <JsonConverterModal isOpen={isJsonConverterOpen} onClose={() => setIsJsonConverterOpen(false)} />
        )}
      </Suspense>
      <ClearWorkspaceDialog />
      <OfflineIndicator />
      <Toaster
        position="bottom-right"
        toastOptions={{
          duration: 3000,
          style: {
            background: '#363636',
            color: '#fff',
          },
          success: {
            duration: 3000,
            iconTheme: {
              primary: '#10b981',
              secondary: '#fff',
            },
          },
          error: {
            duration: 4000,
            iconTheme: {
              primary: '#ef4444',
              secondary: '#fff',
            },
          },
        }}
      />
    </div>
  )
}
