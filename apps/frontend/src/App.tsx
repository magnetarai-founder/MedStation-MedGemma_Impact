import { useState, useEffect, Suspense } from 'react'
import { WelcomeScreen } from './components/WelcomeScreen'
import { useNavigationStore } from './stores/navigationStore'
import { useEditorStore } from './stores/editorStore'
import { initializeSecurityMonitor, cleanupSecurityMonitor } from './lib/securityMonitor'
import { useModelSync } from './hooks/useModelSync'
import { useAppBootstrap } from './hooks/useAppBootstrap'
import { useModelPreload } from './hooks/useModelPreload'
import { AppShell } from './components/layout/AppShell'
import { lazyNamed } from './utils/lazyWithRetry'
import * as settingsApi from './lib/settingsApi'

const SetupWizard = lazyNamed(() => import('./components/SetupWizard/SetupWizard'), 'default')

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

  // Bootstrap auth and session
  const {
    authState,
    setAuthState,
    isLoading,
    userSetupComplete,
    setUserSetupComplete,
    currentUserId,
    setCurrentUserId,
  } = useAppBootstrap()

  // Enable model preloading
  useModelPreload()

  const { activeTab, setActiveTab } = useNavigationStore()
  const { setCode } = useEditorStore()

  // Modal state
  const [isLibraryOpen, setIsLibraryOpen] = useState(false)
  const [isProjectLibraryOpen, setIsProjectLibraryOpen] = useState(false)
  const [isCodeChatSettingsOpen, setIsCodeChatSettingsOpen] = useState(false)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [isJsonConverterOpen, setIsJsonConverterOpen] = useState(false)
  const [isQueryHistoryOpen, setIsQueryHistoryOpen] = useState(false)
  const [libraryInitialCode, setLibraryInitialCode] = useState<{ name: string; content: string } | null>(null)
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

  // Handle run query from query history modal
  const handleRunQuery = (query: string) => {
    setCode(query)
    setActiveTab('database')
  }

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

  // Welcome Screen (always shown first if not authenticated)
  if (authState === 'welcome') {
    return (
      <WelcomeScreen
        onLoginSuccess={(token, userId) => {
          setCurrentUserId(userId)
          setAuthState('checking') // Will check per-user setup status next
        }}
      />
    )
  }

  // Loading state
  if (isLoading || authState === 'checking') {
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

  // Per-user setup wizard (shown after auth if user hasn't completed setup)
  if (userSetupComplete === false) {
    return (
      <Suspense fallback={<LoadingSpinner />}>
        <SetupWizard
          onComplete={() => {
            setUserSetupComplete(true)
            setAuthState('authenticated')
          }}
        />
      </Suspense>
    )
  }

  // Main app (authenticated)
  if (authState !== 'authenticated') {
    return null
  }

  return (
    <AppShell
      activeTab={activeTab}
      onTabChange={setActiveTab}
      isSettingsOpen={isSettingsOpen}
      setIsSettingsOpen={setIsSettingsOpen}
      isLibraryOpen={isLibraryOpen}
      setIsLibraryOpen={setIsLibraryOpen}
      isProjectLibraryOpen={isProjectLibraryOpen}
      setIsProjectLibraryOpen={setIsProjectLibraryOpen}
      isCodeChatSettingsOpen={isCodeChatSettingsOpen}
      setIsCodeChatSettingsOpen={setIsCodeChatSettingsOpen}
      isJsonConverterOpen={isJsonConverterOpen}
      setIsJsonConverterOpen={setIsJsonConverterOpen}
      isQueryHistoryOpen={isQueryHistoryOpen}
      setIsQueryHistoryOpen={setIsQueryHistoryOpen}
      selectedFile={selectedFile}
      onFileSelect={handleFileSelect}
      onLoadQuery={handleLoadQuery}
      libraryInitialCode={libraryInitialCode}
      setLibraryInitialCode={setLibraryInitialCode}
      onRunQuery={handleRunQuery}
    />
  )
}
