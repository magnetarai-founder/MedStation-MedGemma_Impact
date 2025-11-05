/**
 * DiffPreviewModal - Shows unified diff before saving
 * Uses Continue's streamDiff pattern
 */

import { X, Save, AlertTriangle } from 'lucide-react'

interface DiffStats {
  additions: number
  deletions: number
  total_changes: number
}

interface DiffPreviewModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  diffText: string
  stats: DiffStats
  filePath: string
  riskLevel?: string
  riskReason?: string
}

export function DiffPreviewModal({
  isOpen,
  onClose,
  onConfirm,
  diffText,
  stats,
  filePath,
  riskLevel,
  riskReason
}: DiffPreviewModalProps) {
  if (!isOpen) return null

  const getRiskColor = (level?: string) => {
    switch (level) {
      case 'Critical': return 'text-red-600 bg-red-50 dark:bg-red-900/20'
      case 'High Risk': return 'text-orange-600 bg-orange-50 dark:bg-orange-900/20'
      case 'Medium Risk': return 'text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20'
      case 'Low Risk': return 'text-blue-600 bg-blue-50 dark:bg-blue-900/20'
      default: return 'text-green-600 bg-green-50 dark:bg-green-900/20'
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Review Changes
            </h2>
            <p className="text-sm text-gray-500 mt-0.5">{filePath}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Stats */}
        <div className="px-6 py-3 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Changes:</span>
              <span className="text-sm">
                <span className="text-green-600 dark:text-green-400">+{stats.additions}</span>
                {' / '}
                <span className="text-red-600 dark:text-red-400">-{stats.deletions}</span>
              </span>
            </div>

            {riskLevel && (
              <div className={`flex items-center gap-2 px-3 py-1 rounded-md ${getRiskColor(riskLevel)}`}>
                <AlertTriangle className="w-4 h-4" />
                <span className="text-sm font-medium">{riskLevel}</span>
                {riskReason && (
                  <span className="text-xs">— {riskReason}</span>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Diff Content */}
        <div className="flex-1 overflow-auto p-6">
          <pre className="text-sm font-mono bg-gray-900 dark:bg-black text-gray-100 p-4 rounded-lg overflow-x-auto">
            {diffText.split('\n').map((line, idx) => (
              <div
                key={idx}
                className={`${
                  line.startsWith('+') && !line.startsWith('+++')
                    ? 'bg-green-900/30 text-green-300'
                    : line.startsWith('-') && !line.startsWith('---')
                    ? 'bg-red-900/30 text-red-300'
                    : line.startsWith('@@')
                    ? 'text-cyan-400 font-semibold'
                    : 'text-gray-400'
                }`}
              >
                {line || ' '}
              </div>
            ))}
          </pre>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors"
          >
            <Save className="w-4 h-4" />
            Save Changes
          </button>
        </div>
      </div>
    </div>
  )
}
