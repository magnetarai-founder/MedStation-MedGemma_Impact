import { useState, useEffect, lazy, Suspense } from 'react'
import { Toaster } from 'react-hot-toast'
import { FileUpload } from './components/FileUpload'
import { SidebarTabs } from './components/SidebarTabs'
import { Header } from './components/Header'
import { ResizablePanels } from './components/ResizablePanels'
import { ResizableSidebar } from './components/ResizableSidebar'
import { NavigationRail } from './components/NavigationRail'
import { Login } from './components/Login'
import { useSessionStore } from './stores/sessionStore'
import { useNavigationStore } from './stores/navigationStore'
import { useEditorStore } from './stores/editorStore'
import { useChatStore } from './stores/chatStore'
import { useUserStore } from './stores/userStore'
import { api } from './lib/api'
import { ClearWorkspaceDialog } from './components/ClearWorkspaceDialog'
import { OfflineIndicator } from './components/OfflineIndicator'
import * as settingsApi from './lib/settingsApi'
import { FolderOpen, Clock, FileJson } from 'lucide-react'
import { initializeSecurityMonitor, cleanupSecurityMonitor } from './lib/securityMonitor'
import { useModelSync } from './hooks/useModelSync'

// Lazy load heavy components for code splitting
const ChatSidebar = lazy(() => import('./components/ChatSidebar').then(m => ({ default: m.ChatSidebar })))
const ChatWindow = lazy(() => import('./components/ChatWindow').then(m => ({ default: m.ChatWindow })))
const CodeWorkspace = lazy(() => import('./components/CodeWorkspace').then(m => ({ default: m.CodeWorkspace })))
const CodeSidebar = lazy(() => import('./components/CodeSidebar').then(m => ({ default: m.CodeSidebar })))
const TeamWorkspace = lazy(() => import('./components/TeamWorkspace').then(m => ({ default: m.TeamWorkspace })))

// Lazy load modals (only loaded when opened)
const SettingsModal = lazy(() => import('./components/SettingsModal').then(m => ({ default: m.SettingsModal })))
const LibraryModal = lazy(() => import('./components/LibraryModal').then(m => ({ default: m.LibraryModal })))
const ProjectLibraryModal = lazy(() => import('./components/ProjectLibraryModal').then(m => ({ default: m.ProjectLibraryModal })))
const CodeChatSettingsModal = lazy(() => import('./components/CodeChatSettingsModal').then(m => ({ default: m.CodeChatSettingsModal })))
const JsonConverterModal = lazy(() => import('./components/JsonConverterModal').then(m => ({ default: m.JsonConverterModal })))
const QueryHistoryModal = lazy(() => import('./components/QueryHistoryModal').then(m => ({ default: m.QueryHistoryModal })))
const ServerControlModal = lazy(() => import('./components/ServerControlModal').then(m => ({ default: m.ServerControlModal })))

// Loading spinner component for Suspense fallbacks
const LoadingSpinner = () => (
  <div className="h-full w-full flex items-center justify-center">
    <div className="relative w-12 h-12">
      <div className="absolute inset-0 bg-gradient-to-br from-primary-500 to-primary-700 rounded-full animate-pulse"></div>
      <div className="absolute inset-2 bg-gradient-to-br from-blue-300 to-primary-400 rounded-full"></div>
    </div>
  </div>
)

export default function App() {
  // Enable global model syncing (polls every 5 seconds for model changes)
  useModelSync()

  const { sessionId, setSessionId, clearSession } = useSessionStore()
  const { activeTab, setActiveTab } = useNavigationStore()
  const { setCode } = useEditorStore()
  const { settings } = useChatStore()
  const { fetchUser, user } = useUserStore()
  const [isLoading, setIsLoading] = useState(true)
  const [isLibraryOpen, setIsLibraryOpen] = useState(false)
  const [isProjectLibraryOpen, setIsProjectLibraryOpen] = useState(false)
  const [isCodeChatSettingsOpen, setIsCodeChatSettingsOpen] = useState(false)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [isJsonConverterOpen, setIsJsonConverterOpen] = useState(false)
  const [isQueryHistoryOpen, setIsQueryHistoryOpen] = useState(false)
  const [isServerControlsOpen, setIsServerControlsOpen] = useState(false)
  const [libraryInitialCode, setLibraryInitialCode] = useState<{ name: string; content: string } | null>(null)
  const [authState, setAuthState] = useState<'checking' | 'login' | 'authenticated'>('checking')
  const [selectedFile, setSelectedFile] = useState<string | null>(null)

  // Handle loading query from library into editor
  const handleLoadQuery = (query: settingsApi.SavedQuery) => {
    setCode(query.query)
    setIsLibraryOpen(false)
  }

  // Handle file selection from Code Tab file browser
  const handleFileSelect = async (fileId: string, isAbsolute?: boolean) => {
    setSelectedFile(fileId)

    try {
      const response = await fetch(`/api/v1/code/files/${fileId}`)
      if (!response.ok) {
        console.error('Failed to load file:', response.statusText)
        return
      }

      const file = await response.json()
      setCode(file.content || '')
    } catch (error) {
      console.error('Error loading file:', error)
    }
  }

  // Check authentication status on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        // Check if we have a stored token
        const token = localStorage.getItem('auth_token')

        if (token) {
          // Token exists - validate it by fetching user
          try {
            await fetchUser()
            setAuthState('authenticated')
          } catch (error) {
            // Token invalid - clear and show login
            localStorage.removeItem('auth_token')
            localStorage.removeItem('user')
            setAuthState('login')
          }
        } else {
          // No token - show login
          setAuthState('login')
        }
      } catch (error) {
        console.error('Failed to check auth:', error)
        setAuthState('login')
      } finally {
        setIsLoading(false)
      }
    }

    checkAuth()
  }, [])

  // Initialize user and session after authentication
  useEffect(() => {
    if (authState !== 'authenticated') return

    const initApp = async () => {
      try {
        // Fetch or create user identity
        await fetchUser()

        // Create session
        const response = await api.createSession()
        setSessionId(response.session_id)
      } catch (error) {
        console.error('Failed to initialize app:', error)
      }
    }

    initApp()

    // Cleanup on unmount
    return () => {
      if (sessionId) {
        api.deleteSession(sessionId).catch(console.error)
      }
    }
  }, [authState])

  // Pre-load default AI model after session is created
  useEffect(() => {
    // Only preload if we have a valid session
    if (!sessionId) return
    if (!localStorage.getItem('auth_token')) return

    const preloadDefaultModel = async () => {
      try {
        console.log(`Pre-loading default model: ${settings.defaultModel}`)
        await api.preloadModel(settings.defaultModel, '1h')
        console.log(`✓ Model '${settings.defaultModel}' pre-loaded successfully`)
      } catch (error: any) {
        // Non-critical - models load on first use anyway
        console.debug('Model preload failed:', error?.response?.status || error.message)
      }
    }

    // Delay to ensure Ollama server is ready
    const timeoutId = setTimeout(preloadDefaultModel, 3000)
    return () => clearTimeout(timeoutId)
  }, [sessionId, settings.defaultModel])

  // Handle open library with pre-filled code from CodeEditor
  useEffect(() => {
    const handleOpenLibraryWithCode = (event: CustomEvent) => {
      const { name, content } = event.detail
      setLibraryInitialCode({ name, content })
      setIsLibraryOpen(true)
    }

    const handleOpenLibrary = () => {
      setIsLibraryOpen(true)
    }

    window.addEventListener('open-library-with-code', handleOpenLibraryWithCode as EventListener)
    window.addEventListener('open-library', handleOpenLibrary as EventListener)
    return () => {
      window.removeEventListener('open-library-with-code', handleOpenLibraryWithCode as EventListener)
      window.removeEventListener('open-library', handleOpenLibrary as EventListener)
    }
  }, [])

  // Initialize security monitor (auto-lock, screenshot blocking)
  useEffect(() => {
    initializeSecurityMonitor()

    return () => {
      cleanupSecurityMonitor()
    }
  }, [])

  // Loading state
  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="relative w-16 h-16 mx-auto mb-4">
            <div className="absolute inset-0 bg-gradient-to-br from-primary-500 to-primary-700 rounded-full animate-pulse"></div>
            <div className="absolute inset-2 bg-gradient-to-br from-blue-300 to-primary-400 rounded-full"></div>
          </div>
          <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">ElohimOS</p>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Equipping the global Church...</p>
        </div>
      </div>
    )
  }

  // Login screen (with "Create Account" button to show setup wizard)
  if (authState === 'login') {
    return <Login onLogin={(token) => setAuthState('authenticated')} />
  }

  // Main app (authenticated)
  if (authState !== 'authenticated') {
    return null
  }

  return (
    <div className="h-screen flex flex-col">
      <Header onOpenServerControls={() => setIsServerControlsOpen(true)} />

      <div className="flex-1 flex overflow-hidden min-h-0">
        <NavigationRail
          activeTab={activeTab}
          onTabChange={setActiveTab}
          onOpenSettings={() => setIsSettingsOpen(true)}
          onOpenServerControls={() => setIsServerControlsOpen(true)}
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

          {/* Code Tab */}
          <div
            className="absolute inset-0 flex"
            style={{
              display: activeTab === 'code' ? 'flex' : 'none'
            }}
          >
            <Suspense fallback={<LoadingSpinner />}>
              <ResizableSidebar
                initialWidth={320}
                minWidth={320}
                storageKey="ns.codeSidebarWidth"
                left={
                  <CodeSidebar
                    onFileSelect={handleFileSelect}
                    selectedFile={selectedFile}
                    onOpenLibrary={() => setIsProjectLibraryOpen(true)}
                    onOpenSettings={() => setIsCodeChatSettingsOpen(true)}
                  />
                }
                right={<CodeWorkspace />}
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

        </div>
      </div>

      <Suspense fallback={null}>
        {isLibraryOpen && (
          <LibraryModal
            isOpen={isLibraryOpen}
            onClose={() => {
              setIsLibraryOpen(false)
              setLibraryInitialCode(null)
            }}
            initialCodeData={libraryInitialCode}
            onLoadQuery={handleLoadQuery}
          />
        )}
      </Suspense>
      <Suspense fallback={null}>
        {isProjectLibraryOpen && (
          <ProjectLibraryModal
            isOpen={isProjectLibraryOpen}
            onClose={() => setIsProjectLibraryOpen(false)}
          />
        )}
      </Suspense>
      <Suspense fallback={null}>
        {isCodeChatSettingsOpen && (
          <CodeChatSettingsModal
            isOpen={isCodeChatSettingsOpen}
            onClose={() => setIsCodeChatSettingsOpen(false)}
          />
        )}
      </Suspense>
      <Suspense fallback={null}>
        {isQueryHistoryOpen && (
          <QueryHistoryModal
            isOpen={isQueryHistoryOpen}
            onClose={() => setIsQueryHistoryOpen(false)}
            onRunQuery={(query) => {
              setCode(query)
              setActiveTab('database')
            }}
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
      <Suspense fallback={null}>
        {isServerControlsOpen && (
          <ServerControlModal isOpen={isServerControlsOpen} onClose={() => setIsServerControlsOpen(false)} />
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
