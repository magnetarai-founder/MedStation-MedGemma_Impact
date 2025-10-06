import { useState } from 'react'
import { SavedQueriesTree } from './SavedQueriesTree'
import { QueryHistoryListNew } from './QueryHistoryListNew'

export function QueryHistoryPanel() {
  const [leftWidth, setLeftWidth] = useState(50) // percentage

  return (
    <div className="h-full flex">
      {/* Left pane - Saved Queries */}
      <div
        style={{ width: `${leftWidth}%` }}
        className="min-w-[200px] border-r border-gray-200 dark:border-gray-800"
      >
        <SavedQueriesTree />
      </div>

      {/* Resize handle */}
      <div
        className="w-1 bg-gray-200 dark:bg-gray-800 hover:bg-primary-500 cursor-col-resize"
        onMouseDown={(e) => {
          e.preventDefault()
          const startX = e.clientX
          const startWidth = leftWidth

          const handleMouseMove = (e: MouseEvent) => {
            const container = document.querySelector('.h-full.flex') as HTMLElement
            if (!container) return

            const containerWidth = container.offsetWidth
            const deltaX = e.clientX - startX
            const deltaPercent = (deltaX / containerWidth) * 100
            const newWidth = Math.min(80, Math.max(20, startWidth + deltaPercent))

            setLeftWidth(newWidth)
          }

          const handleMouseUp = () => {
            document.removeEventListener('mousemove', handleMouseMove)
            document.removeEventListener('mouseup', handleMouseUp)
            document.body.style.cursor = ''
            document.body.style.userSelect = ''
          }

          document.addEventListener('mousemove', handleMouseMove)
          document.addEventListener('mouseup', handleMouseUp)
          document.body.style.cursor = 'col-resize'
          document.body.style.userSelect = 'none'
        }}
      />

      {/* Right pane - Query History */}
      <div
        style={{ width: `${100 - leftWidth}%` }}
        className="min-w-[200px]"
      >
        <QueryHistoryListNew />
      </div>
    </div>
  )
}
