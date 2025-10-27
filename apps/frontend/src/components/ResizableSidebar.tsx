import { useCallback, useEffect, useRef, useState } from 'react'
import { GripVertical } from 'lucide-react'

type Props = {
  left: React.ReactNode
  right: React.ReactNode
  initialWidth?: number // px
  minWidth?: number // px
  maxWidthPercent?: number // % of container width
  storageKey?: string
}

export function ResizableSidebar({
  left,
  right,
  initialWidth = 320,
  minWidth = 320,
  maxWidthPercent = 60,
  storageKey = 'ns.sidebarWidth',
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [isResizing, setIsResizing] = useState(false)
  const [width, setWidth] = useState<number>(() => {
    const saved = Number(localStorage.getItem(storageKey))
    return Number.isFinite(saved) && saved >= minWidth ? saved : initialWidth
  })
  const startXRef = useRef(0)
  const startWRef = useRef(width)

  const clamp = useCallback((w: number) => {
    let maxW = Infinity
    if (containerRef.current) {
      maxW = (containerRef.current.offsetWidth * maxWidthPercent) / 100
    }
    const clamped = Math.max(minWidth, Math.min(w, maxW))
    return clamped
  }, [minWidth, maxWidthPercent])

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(true)
    startXRef.current = e.clientX
    startWRef.current = width
  }, [width])

  const onMouseMove = useCallback((e: MouseEvent) => {
    if (!isResizing) return
    const dx = e.clientX - startXRef.current
    setWidth(prev => clamp(startWRef.current + dx))
  }, [isResizing, clamp])

  const onMouseUp = useCallback(() => {
    if (!isResizing) return
    setIsResizing(false)
  }, [isResizing])

  // Persist
  useEffect(() => {
    localStorage.setItem(storageKey, String(width))
  }, [width, storageKey])

  // Global listeners during resize
  useEffect(() => {
    if (!isResizing) return
    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
    document.body.style.cursor = 'ew-resize'
    document.body.style.userSelect = 'none'
    return () => {
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isResizing, onMouseMove, onMouseUp])

  // Re-clamp on container resize
  useEffect(() => {
    const ro = new ResizeObserver(() => setWidth(w => clamp(w)))
    if (containerRef.current) ro.observe(containerRef.current)
    return () => ro.disconnect()
  }, [clamp])

  return (
    <div ref={containerRef} className="flex flex-1 h-full overflow-hidden">
      {/* Left sidebar */}
      <div
        className="h-full glass border-r border-white/30 dark:border-gray-700/40 flex-shrink-0 bg-gray-50/50 dark:bg-gray-800/30"
        style={{ width: `${width}px`, minWidth: `${minWidth}px` }}
      >
        {left}
      </div>

      {/* Drag handle */}
      <div
        className={`relative w-1 cursor-ew-resize group ${isResizing ? 'bg-primary-500' : 'bg-transparent hover:bg-gray-300/50 dark:hover:bg-gray-600/50'}`}
        onMouseDown={onMouseDown}
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize sidebar"
      >
        <div className="absolute inset-y-0 -left-2 -right-2 flex items-center justify-center">
          <div className={`px-2 py-0.5 rounded-full glass-panel ${isResizing ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'} transition-opacity`}>
            <GripVertical className="w-3 h-3 text-gray-600 dark:text-gray-300" />
          </div>
        </div>
      </div>

      {/* Right content */}
      <div className="flex-1 min-w-0 min-h-0 flex flex-col">
        {right}
      </div>
    </div>
  )
}
