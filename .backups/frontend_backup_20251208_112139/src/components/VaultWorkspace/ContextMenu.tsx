/**
 * Generic Context Menu Component
 */

import type { ContextMenuState } from './types'

interface ContextMenuProps {
  contextMenu: ContextMenuState | null
  onClose: () => void
  children: React.ReactNode
}

export function ContextMenu({ contextMenu, onClose, children }: ContextMenuProps) {
  if (!contextMenu) return null

  return (
    <div
      className="fixed z-50 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 py-1 min-w-[180px]"
      style={{ left: contextMenu.x, top: contextMenu.y }}
      onClick={onClose}
    >
      {children}
    </div>
  )
}
