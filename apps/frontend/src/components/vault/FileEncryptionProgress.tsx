/**
 * File Encryption Progress Component
 *
 * Shows real-time progress for encrypting/decrypting large files
 * Displays progress bar, percentage, and estimated time remaining
 */

import { Lock, Unlock, Clock, CheckCircle } from 'lucide-react'

interface FileEncryptionProgressProps {
  fileName: string
  progress: number
  operation: 'encrypting' | 'decrypting'
  fileSize?: number
  isComplete?: boolean
}

export function FileEncryptionProgress({
  fileName,
  progress,
  operation,
  fileSize,
  isComplete = false,
}: FileEncryptionProgressProps) {
  // Estimate time remaining (rough estimate based on typical speeds)
  const estimatedTime = Math.ceil((100 - progress) * 0.5) // seconds

  // Format file size
  const formatFileSize = (bytes: number | undefined): string => {
    if (!bytes) return ''
    const mb = bytes / (1024 * 1024)
    if (mb >= 1000) {
      return `${(mb / 1024).toFixed(2)} GB`
    }
    return `${mb.toFixed(2)} MB`
  }

  // Format time
  const formatTime = (seconds: number): string => {
    if (seconds < 60) {
      return `${seconds}s`
    }
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}m ${remainingSeconds}s`
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isComplete ? (
            <div className="p-2 bg-green-50 dark:bg-green-900/30 rounded-lg">
              <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
          ) : operation === 'encrypting' ? (
            <div className="p-2 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
              <Lock className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
          ) : (
            <div className="p-2 bg-purple-50 dark:bg-purple-900/30 rounded-lg">
              <Unlock className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
          )}

          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
              {isComplete
                ? operation === 'encrypting'
                  ? 'Encryption Complete'
                  : 'Decryption Complete'
                : operation === 'encrypting'
                ? 'Encrypting'
                : 'Decrypting'}{' '}
              {fileName}
            </div>
            {fileSize && (
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {formatFileSize(fileSize)}
              </div>
            )}
          </div>
        </div>

        <div className="text-right">
          <div
            className={`text-lg font-bold ${
              isComplete
                ? 'text-green-600 dark:text-green-400'
                : operation === 'encrypting'
                ? 'text-blue-600 dark:text-blue-400'
                : 'text-purple-600 dark:text-purple-400'
            }`}
          >
            {progress.toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="relative h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`absolute inset-y-0 left-0 rounded-full transition-all duration-300 ${
            isComplete
              ? 'bg-gradient-to-r from-green-500 to-green-600'
              : operation === 'encrypting'
              ? 'bg-gradient-to-r from-blue-500 to-blue-600'
              : 'bg-gradient-to-r from-purple-500 to-purple-600'
          }`}
          style={{ width: `${progress}%` }}
        >
          {/* Animated shimmer effect */}
          {!isComplete && (
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
          )}
        </div>
      </div>

      {/* Status Info */}
      {!isComplete && progress < 100 && (
        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
          <div className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            <span>Estimated time: ~{formatTime(estimatedTime)}</span>
          </div>
          <span>Processing...</span>
        </div>
      )}

      {isComplete && (
        <div className="text-xs text-green-600 dark:text-green-400 font-medium">
          ✓ {operation === 'encrypting' ? 'File encrypted successfully' : 'File decrypted successfully'}
        </div>
      )}
    </div>
  )
}

/**
 * Minimal Progress Bar (for inline use)
 */
export function FileEncryptionProgressBar({
  progress,
  operation,
}: {
  progress: number
  operation: 'encrypting' | 'decrypting'
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-600 dark:text-gray-400">
          {operation === 'encrypting' ? '🔒 Encrypting...' : '🔓 Decrypting...'}
        </span>
        <span className="font-medium text-gray-700 dark:text-gray-300">{progress.toFixed(0)}%</span>
      </div>
      <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            operation === 'encrypting'
              ? 'bg-blue-500'
              : 'bg-purple-500'
          }`}
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  )
}
