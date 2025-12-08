import { useState, useRef, useEffect, useCallback } from 'react'
import { GripVertical } from 'lucide-react'
import { CodeEditor } from './CodeEditor'
import { ResultsTable } from './ResultsTable'

export function ResizablePanels() {
  const [topHeight, setTopHeight] = useState(33) // percentage
  const [isResizing, setIsResizing] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const startYRef = useRef(0)
  const startHeightRef = useRef(0)

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(true)
    startYRef.current = e.clientY
    startHeightRef.current = topHeight
  }, [topHeight])

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isResizing || !containerRef.current) return

    const containerHeight = containerRef.current.offsetHeight
    const deltaY = e.clientY - startYRef.current
    const deltaPercent = (deltaY / containerHeight) * 100
    const newHeight = Math.min(80, Math.max(20, startHeightRef.current + deltaPercent))
    
    setTopHeight(newHeight)
  }, [isResizing])

  const handleMouseUp = useCallback(() => {
    setIsResizing(false)
  }, [])

  useEffect(() => {
    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'ns-resize'
      document.body.style.userSelect = 'none'
      
      return () => {
        document.removeEventListener('mousemove', handleMouseMove)
        document.removeEventListener('mouseup', handleMouseUp)
        document.body.style.cursor = ''
        document.body.style.userSelect = ''
      }
    }
  }, [isResizing, handleMouseMove, handleMouseUp])

  return (
    <div ref={containerRef} className="flex-1 min-h-0 flex flex-col relative">
      {/* Code Editor */}
      <div style={{ height: `${topHeight}%` }} className="min-h-[150px]">
        <CodeEditor />
      </div>
      
      {/* Resizable Handle */}
      <div
        className={`
          relative h-1.5 cursor-ns-resize group
          ${isResizing ? 'bg-primary-500' : 'bg-gray-500 dark:bg-gray-500 hover:bg-gray-600 dark:hover:bg-gray-400'}
          transition-colors
        `}
        onMouseDown={handleMouseDown}
      >
        <div className="absolute inset-x-0 -top-2 -bottom-2 flex items-center justify-center">
          <div className={`
            px-2 py-0.5 rounded-full bg-gray-200 dark:bg-gray-700 
            ${isResizing ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}
            transition-opacity
          `}>
            <GripVertical className="w-3 h-3 text-gray-500 dark:text-gray-400" />
          </div>
        </div>
      </div>
      
      {/* Results Table */}
      <div style={{ height: `${100 - topHeight}%` }} className="min-h-[150px] overflow-hidden">
        <ResultsTable />
      </div>
    </div>
  )
}
