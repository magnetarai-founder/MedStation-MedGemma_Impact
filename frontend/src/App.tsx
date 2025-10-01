import { useState, useEffect } from 'react'
import { FileUpload } from './components/FileUpload'
import { JsonFileUpload } from './components/JsonFileUpload'
import { SidebarTabs } from './components/SidebarTabs'
import { Header } from './components/Header'
import { ResizablePanels } from './components/ResizablePanels'
import { JsonResizablePanels } from './components/JsonResizablePanels'
import { ResizableSidebar } from './components/ResizableSidebar'
import { NavigationRail } from './components/NavigationRail'
import { ChatSidebar } from './components/ChatSidebar'
import { ChatWindow } from './components/ChatWindow'
import { useSessionStore } from './stores/sessionStore'
import { useNavigationStore } from './stores/navigationStore'
import { api } from './lib/api'
import { SettingsModal } from './components/SettingsModal'

export default function App() {
  const { sessionId, setSessionId, clearSession } = useSessionStore()
  const { activeTab, setActiveTab } = useNavigationStore()
  const [isLoading, setIsLoading] = useState(true)

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

  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="relative w-16 h-16 mx-auto mb-4">
            <div className="absolute inset-0 bg-gradient-to-br from-primary-500 to-primary-700 rounded-full animate-pulse"></div>
            <div className="absolute inset-2 bg-gradient-to-br from-blue-300 to-primary-400 rounded-full"></div>
          </div>
          <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">OmniStudio</p>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Initializing platform...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col">
      <Header />

      <div className="flex-1 flex overflow-hidden min-h-0">
        <NavigationRail activeTab={activeTab} onTabChange={setActiveTab} />

        {activeTab === 'chat' ? (
          <ResizableSidebar
            initialWidth={320}
            minWidth={280}
            storageKey="ns.chatSidebarWidth"
            left={<ChatSidebar />}
            right={<ChatWindow />}
          />
        ) : (
          <ResizableSidebar
            initialWidth={320}
            minWidth={320}
            left={
              <div className="h-full flex flex-col">
                <div className="p-4 border-b border-gray-200 dark:border-gray-800">
                  {activeTab === 'sql' ? <FileUpload /> : <JsonFileUpload />}
                </div>
                <div className="flex-1 overflow-hidden">
                  <SidebarTabs />
                </div>
              </div>
            }
            right={activeTab === 'sql' ? <ResizablePanels /> : <JsonResizablePanels />}
          />
        )}
      </div>
      <SettingsModal />
    </div>
  )
}
