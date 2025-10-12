import { useState, useRef } from 'react'
import { Database, SlidersHorizontal, MessageSquare, Users2, Code2 } from 'lucide-react'
import { useNavigationStore, type NavTab } from '../stores/navigationStore'

interface NavigationRailProps {
  activeTab: NavTab
  onTabChange: (tab: NavTab) => void
  onOpenSettings: () => void
}

// Navigation item configuration
const NAV_ITEMS = {
  team: { icon: Users2, label: 'Team Chat', isTab: true },
  chat: { icon: MessageSquare, label: 'AI Chat', isTab: true },
  editor: { icon: Code2, label: 'Code Editor', isTab: true },
  database: { icon: Database, label: 'Database', isTab: true },
} as const

export function NavigationRail({ activeTab, onTabChange, onOpenSettings }: NavigationRailProps) {
  const { navOrder, setNavOrder } = useNavigationStore()
  const [isDragging, setIsDragging] = useState(false)
  const [draggedItemId, setDraggedItemId] = useState<string | null>(null)
  const [dropTargetIndex, setDropTargetIndex] = useState<number | null>(null)
  const [cmdPressed, setCmdPressed] = useState(false)
  const dragStartY = useRef<number>(0)
  const itemRefs = useRef<Map<string, HTMLDivElement>>(new Map())

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
      {/* Top section with navigation items */}
      <div className="flex flex-col items-center gap-3 pt-5">
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
    </div>
  )
}
