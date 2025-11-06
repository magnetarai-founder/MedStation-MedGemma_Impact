/**
 * TerminalModal - Modal wrapper for terminal view
 *
 * Opened from global </> button in header
 */

import { TerminalView } from './TerminalView'

interface TerminalModalProps {
  isOpen: boolean
  onClose: () => void
}

export function TerminalModal({ isOpen, onClose }: TerminalModalProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="w-full h-full max-w-7xl max-h-[90vh] m-4 bg-gray-900 rounded-lg shadow-2xl overflow-hidden">
        <TerminalView onClose={onClose} autoSpawn={true} />
      </div>
    </div>
  )
}
