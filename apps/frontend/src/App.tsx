import { useState, useEffect } from 'react'
import { FileUpload } from './components/FileUpload'
import { SidebarTabs } from './components/SidebarTabs'
import { Header } from './components/Header'
import { ResizablePanels } from './components/ResizablePanels'
import { ResizableSidebar } from './components/ResizableSidebar'
import { NavigationRail } from './components/NavigationRail'
import { ChatSidebar } from './components/ChatSidebar'
import { ChatWindow } from './components/ChatWindow'
import { SettingsModal } from './components/SettingsModal'
import { LibraryModal } from './components/LibraryModal'
import { JsonConverterModal } from './components/JsonConverterModal'
import { TeamChat } from './components/TeamChat'
import { useSessionStore } from './stores/sessionStore'
import { useNavigationStore } from './stores/navigationStore'
import { useEditorStore } from './stores/editorStore'
import { useChatStore } from './stores/chatStore'
import { api } from './lib/api'
import { ClearWorkspaceDialog } from './components/ClearWorkspaceDialog'
import * as settingsApi from './lib/settingsApi'

export default function App() {
  const { sessionId, setSessionId, clearSession } = useSessionStore()
  const { activeTab, setActiveTab } = useNavigationStore()
  const { setCode } = useEditorStore()
  const { settings } = useChatStore()
  const [isLoading, setIsLoading] = useState(true)
  const [isLibraryOpen, setIsLibraryOpen] = useState(false)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [isJsonConverterOpen, setIsJsonConverterOpen] = useState(false)
  const [libraryInitialCode, setLibraryInitialCode] = useState<{ name: string; content: string } | null>(null)

  // Handle loading query from library into editor
  const handleLoadQuery = (query: settingsApi.SavedQuery) => {
    setCode(query.query)
    setIsLibraryOpen(false)
  }

  // Initialize session on mount
  useEffect(() => {
    const initSession = async () => {
      try {
        const response = await api.createSession()
        setSessionId(response.session_id)
      } catch (error) {
        console.error('Failed to create session:', error)
      } finally {
        setIsLoading(false)
      }
    }

    initSession()

    // Cleanup on unmount
    return () => {
      if (sessionId) {
        api.deleteSession(sessionId).catch(console.error)
      }
    }
  }, [])

  // Pre-load default AI model on mount
  useEffect(() => {
    const preloadDefaultModel = async () => {
      try {
        console.log(`Pre-loading default model: ${settings.defaultModel}`)
        await api.preloadModel(settings.defaultModel, '1h')
        console.log(`✓ Model '${settings.defaultModel}' pre-loaded successfully`)
      } catch (error) {
        console.warn('Failed to pre-load model:', error)
        // Non-critical error - don't block app initialization
      }
    }

    // Small delay to ensure Ollama server is ready
    const timeoutId = setTimeout(preloadDefaultModel, 2000)
    return () => clearTimeout(timeoutId)
  }, [settings.defaultModel])

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

  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="relative w-16 h-16 mx-auto mb-4">
            <div className="absolute inset-0 bg-gradient-to-br from-primary-500 to-primary-700 rounded-full animate-pulse"></div>
            <div className="absolute inset-2 bg-gradient-to-br from-blue-300 to-primary-400 rounded-full"></div>
          </div>
          <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">Neutron Star</p>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Initializing platform...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col">
      <Header />

      <div className="flex-1 flex overflow-hidden min-h-0">
        <NavigationRail
          activeTab={activeTab}
          onTabChange={setActiveTab}
          onOpenLibrary={() => setIsLibraryOpen(true)}
          onOpenSettings={() => setIsSettingsOpen(true)}
          onOpenJsonConverter={() => setIsJsonConverterOpen(true)}
        />

        <div className="flex-1 flex flex-col min-h-0 min-w-0 relative">
          {/* Team Chat Tab */}
          <div
            className="absolute inset-0 flex"
            style={{
              display: activeTab === 'team' ? 'flex' : 'none'
            }}
          >
            <TeamChat />
          </div>

          {/* AI Chat Tab */}
          <div
            className="absolute inset-0 flex"
            style={{
              display: activeTab === 'chat' ? 'flex' : 'none'
            }}
          >
            <ResizableSidebar
              initialWidth={320}
              minWidth={280}
              storageKey="ns.chatSidebarWidth"
              left={<ChatSidebar />}
              right={<ChatWindow />}
            />
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
                  <div className="p-4 border-b border-gray-200 dark:border-gray-800">
                    <FileUpload />
                  </div>
                  <div className="flex-1 overflow-hidden">
                    <SidebarTabs />
                  </div>
                </div>
              }
              right={<ResizablePanels />}
            />
          </div>

          {/* History/Queries Tab */}
          <div
            className="absolute inset-0 flex"
            style={{
              display: activeTab === 'queries' ? 'flex' : 'none'
            }}
          >
            {/* TODO: Queries/History view will go here */}
            <div className="flex-1 flex items-center justify-center text-gray-500">
              Query History - Coming Soon
            </div>
          </div>
        </div>
      </div>

      <LibraryModal
        isOpen={isLibraryOpen}
        onClose={() => {
          setIsLibraryOpen(false)
          setLibraryInitialCode(null)
        }}
        initialCodeData={libraryInitialCode}
        onLoadQuery={handleLoadQuery}
      />
      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
      <JsonConverterModal isOpen={isJsonConverterOpen} onClose={() => setIsJsonConverterOpen(false)} />
      <ClearWorkspaceDialog />
    </div>
  )
}
