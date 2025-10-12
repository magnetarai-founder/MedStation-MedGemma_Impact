import { useState, useRef, useEffect } from 'react'
import { Database, SlidersHorizontal, FolderOpen, FileJson, MessageSquare, Users2, History } from 'lucide-react'
import { useNavigationStore, type NavTab } from '../stores/navigationStore'
import { useOllamaStore } from '../stores/ollamaStore'
import { ShutdownModal, RestartModal } from './OllamaServerModals'
import { api } from '../lib/api'

interface NavigationRailProps {
  activeTab: NavTab
  onTabChange: (tab: NavTab) => void
  onOpenLibrary: () => void
  onOpenSettings: () => void
  onOpenJsonConverter: () => void
}

// Navigation item configuration
const NAV_ITEMS = {
  team: { icon: Users2, label: 'Team Chat', isTab: true },
  chat: { icon: MessageSquare, label: 'AI Chat', isTab: true },
  database: { icon: Database, label: 'Database', isTab: true },
  queries: { icon: History, label: 'History', isTab: true },
  json: { icon: FileJson, label: 'JSON Converter', isTab: false },
  library: { icon: FolderOpen, label: 'Library', isTab: false },
} as const

export function NavigationRail({ activeTab, onTabChange, onOpenLibrary, onOpenSettings, onOpenJsonConverter }: NavigationRailProps) {
  const { navOrder, setNavOrder } = useNavigationStore()
  const { serverStatus, fetchServerStatus } = useOllamaStore()
  const [isDragging, setIsDragging] = useState(false)
  const [draggedItemId, setDraggedItemId] = useState<string | null>(null)
  const [dropTargetIndex, setDropTargetIndex] = useState<number | null>(null)
  const [cmdPressed, setCmdPressed] = useState(false)
  const [showShutdownModal, setShowShutdownModal] = useState(false)
  const [showRestartModal, setShowRestartModal] = useState(false)
  const [previousModels, setPreviousModels] = useState<string[]>([])
  const dragStartY = useRef<number>(0)
  const itemRefs = useRef<Map<string, HTMLDivElement>>(new Map())

  // Fetch server status on mount and periodically
  useEffect(() => {
    fetchServerStatus()
    const interval = setInterval(fetchServerStatus, 10000) // Every 10 seconds
    return () => clearInterval(interval)
  }, [])

  // Track Cmd key state
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.metaKey || e.key === 'Meta') {
      setCmdPressed(true)
    }
  }

  const handleKeyUp = (e: KeyboardEvent) => {
    if (!e.metaKey && e.key === 'Meta') {
      setCmdPressed(false)
    }
  }

  // Register keyboard listeners
  useState(() => {
    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('keyup', handleKeyUp)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('keyup', handleKeyUp)
    }
  })

  const handleDragStart = (e: React.DragEvent, itemId: string) => {
    if (!cmdPressed) {
      e.preventDefault()
      return
    }

    setIsDragging(true)
    setDraggedItemId(itemId)
    dragStartY.current = e.clientY

    // Make drag image semi-transparent
    if (e.dataTransfer) {
      e.dataTransfer.effectAllowed = 'move'
      const dragImage = itemRefs.current.get(itemId)
      if (dragImage) {
        e.dataTransfer.setDragImage(dragImage, 28, 28)
      }
    }
  }

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault()
    if (!isDragging || draggedItemId === null) return

    setDropTargetIndex(index)
  }

  const handleDragEnd = () => {
    if (draggedItemId !== null && dropTargetIndex !== null) {
      const newOrder = [...navOrder]
      const draggedIndex = newOrder.indexOf(draggedItemId as any)

      if (draggedIndex !== -1 && draggedIndex !== dropTargetIndex) {
        // Remove from old position
        const [removed] = newOrder.splice(draggedIndex, 1)
        // Insert at new position
        newOrder.splice(dropTargetIndex, 0, removed)
        setNavOrder(newOrder)
      }
    }

    setIsDragging(false)
    setDraggedItemId(null)
    setDropTargetIndex(null)
  }

  const handleItemClick = (itemId: string) => {
    const item = NAV_ITEMS[itemId as keyof typeof NAV_ITEMS]

    if (!item) return

    if (item.isTab) {
      onTabChange(itemId as NavTab)
    } else {
      // Handle modal triggers
      if (itemId === 'json') onOpenJsonConverter()
      if (itemId === 'library') onOpenLibrary()
    }
  }

  const handleLogoClick = () => {
    if (serverStatus.running) {
      // Server is running - show shutdown modal
      setShowRestartModal(false) // Ensure restart modal is closed
      setShowShutdownModal(true)
    } else {
      // Server is off - show restart modal
      setShowShutdownModal(false) // Ensure shutdown modal is closed
      setPreviousModels(serverStatus.loadedModels) // Use last known loaded models
      setShowRestartModal(true)
    }
  }

  const handleShutdownConfirm = async () => {
    try {
      const response = await fetch(`/api/v1/chat/ollama/server/shutdown`, {
        method: 'POST'
      })

      if (response.ok) {
        const data = await response.json()
        // Save models that were loaded before shutdown
        setPreviousModels(data.previously_loaded_models || [])
        // Close modal
        setShowShutdownModal(false)
        // Update server status
        await fetchServerStatus()
      } else {
        alert('Failed to shutdown Ollama server')
      }
    } catch (error) {
      console.error('Failed to shutdown Ollama:', error)
      alert('Failed to shutdown Ollama server')
    }
  }

  const handleRestartConfirm = async (reloadModels: boolean, modelsToLoad: string[]) => {
    try {
      const response = await fetch(
        `/api/v1/chat/ollama/server/restart?reload_models=${reloadModels}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ models_to_load: modelsToLoad })
        }
      )

      if (response.ok) {
        // Close modal
        setShowRestartModal(false)
        // Wait a moment for startup
        setTimeout(async () => {
          await fetchServerStatus()
        }, 3000)
      } else {
        alert('Failed to restart Ollama server')
      }
    } catch (error) {
      console.error('Failed to restart Ollama:', error)
      alert('Failed to restart Ollama server')
    }
  }

  const getButtonClasses = (itemId: string) => {
    const item = NAV_ITEMS[itemId as keyof typeof NAV_ITEMS]
    const isActive = item.isTab && activeTab === itemId
    const isBeingDragged = draggedItemId === itemId
    const isDropTarget = dropTargetIndex !== null && navOrder[dropTargetIndex] === itemId

    let classes = `w-14 h-14 rounded-2xl flex items-center justify-center transition-all cursor-pointer select-none ${
      isActive
        ? 'bg-primary-600/90 text-white shadow-xl backdrop-blur-xl'
        : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-white/60 dark:hover:bg-gray-700/60 hover:shadow-lg'
    }`

    if (cmdPressed) {
      classes += ' cursor-grab active:cursor-grabbing'
    }

    if (isBeingDragged) {
      classes += ' opacity-50 scale-95'
    }

    if (isDropTarget && !isBeingDragged) {
      classes += ' ring-2 ring-primary-500 ring-offset-2 dark:ring-offset-gray-900'
    }

    return classes
  }

  return (
    <div className="w-18 glass flex flex-col items-center">
      {/* Top section with logo */}
      <div className="flex flex-col items-center gap-3">
        {/* Logo at top - Clickable to control Ollama server */}
        <div className="py-5 flex items-center justify-center">
          <button
            onClick={handleLogoClick}
            className="relative w-10 h-10 cursor-pointer group transition-transform hover:scale-110 active:scale-95"
            title={serverStatus.running ? `Ollama Server Running (${serverStatus.modelCount} models loaded) - Click to shutdown` : 'Ollama Server Stopped - Click to start'}
          >
            {/* Outer glow/radiation - shows server status */}
            <div className={`absolute -inset-1 rounded-full blur-sm transition-colors ${
              serverStatus.running
                ? 'bg-green-400/40'
                : 'bg-red-400/30'
            }`}></div>

            {/* Main star body - green when running, red when stopped */}
            <div className={`absolute inset-0 rounded-full shadow-lg transition-colors ${
              serverStatus.running
                ? 'bg-gradient-radial from-green-200 via-green-500 to-green-800 group-hover:from-green-300 group-hover:via-green-600 group-hover:to-green-900'
                : 'bg-gradient-radial from-gray-300 via-gray-500 to-gray-700 group-hover:from-green-200 group-hover:via-green-500 group-hover:to-green-800'
            }`}></div>

            {/* Surface detail - darker spots */}
            <div className={`absolute inset-2 rounded-full transition-colors ${
              serverStatus.running
                ? 'bg-green-700/40'
                : 'bg-gray-600/40 group-hover:bg-green-700/40'
            }`}></div>

            {/* Bright core */}
            <div className={`absolute inset-3 rounded-full transition-colors ${
              serverStatus.running
                ? 'bg-gradient-to-br from-white via-green-100 to-green-300'
                : 'bg-gradient-to-br from-gray-200 via-gray-300 to-gray-400 group-hover:from-white group-hover:via-green-100 group-hover:to-green-300'
            }`}></div>

            {/* Polar emission beams - only show when running */}
            {serverStatus.running && (
              <>
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-0.5 h-2 bg-gradient-to-t from-green-300 to-transparent"></div>
                <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-0.5 h-2 bg-gradient-to-b from-green-300 to-transparent"></div>
              </>
            )}

            {/* Rotating effect with magnetic field indicators */}
            <div className={`absolute inset-0 rounded-full border transition-colors ${
              serverStatus.running
                ? 'border-green-400/50'
                : 'border-gray-400/50 group-hover:border-green-400/50'
            }`}></div>
          </button>
        </div>

        {/* Divider */}
        <div className="w-12 h-px bg-gray-300/30 dark:bg-gray-600/30"></div>

        {/* Draggable navigation items */}
        {navOrder.map((itemId, index) => {
          const item = NAV_ITEMS[itemId as keyof typeof NAV_ITEMS]
          if (!item) return null

          const Icon = item.icon

          return (
            <div
              key={itemId}
              ref={(el) => {
                if (el) itemRefs.current.set(itemId, el)
                else itemRefs.current.delete(itemId)
              }}
              draggable={cmdPressed}
              onDragStart={(e) => handleDragStart(e, itemId)}
              onDragOver={(e) => handleDragOver(e, index)}
              onDragEnd={handleDragEnd}
              onClick={() => !isDragging && handleItemClick(itemId)}
              className={getButtonClasses(itemId)}
              title={cmdPressed ? `Drag to reorder - ${item.label}` : item.label}
            >
              <Icon size={22} />
            </div>
          )
        })}
      </div>

      {/* Spacer */}
      <div className="flex-1"></div>

      {/* Bottom section - Settings (always locked) */}
      <div className="pb-4">
        <button
          onClick={onOpenSettings}
          className="w-14 h-14 rounded-2xl flex items-center justify-center transition-all text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-white/60 dark:hover:bg-gray-700/60 hover:shadow-lg"
          title="Settings"
        >
          <SlidersHorizontal size={22} />
        </button>
      </div>

      {/* Cmd hint overlay */}
      {cmdPressed && (
        <div className="fixed bottom-4 left-20 bg-gray-900 dark:bg-gray-800 text-white px-3 py-2 rounded-lg text-xs font-medium shadow-xl border border-gray-700 z-50">
          Drag to reorder
        </div>
      )}

      {/* Ollama Server Control Modals */}
      <ShutdownModal
        isOpen={showShutdownModal}
        onClose={() => setShowShutdownModal(false)}
        onConfirm={handleShutdownConfirm}
        loadedModels={serverStatus.loadedModels}
      />

      <RestartModal
        isOpen={showRestartModal}
        onClose={() => setShowRestartModal(false)}
        onConfirm={handleRestartConfirm}
        previousModels={previousModels}
      />
    </div>
  )
}
