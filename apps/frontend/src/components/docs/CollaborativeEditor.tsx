/**
 * Collaborative Editor Component
 *
 * Document editor with file locking and real-time presence indicators
 * Shows who else is viewing/editing the document
 */

import { useState, useEffect, useRef } from 'react'
import { Lock, Users, Eye, Edit3, AlertCircle } from 'lucide-react'
import { useQuery, useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'

interface ActiveEditor {
  user_id: string
  user_name: string
  last_seen: string
  is_editing: boolean
}

interface DocumentLock {
  is_locked: boolean
  locked_by_user_id?: string
  locked_by_user_name?: string
  locked_at?: string
}

interface CollaborativeEditorProps {
  docId: string
  content?: string
  onContentChange?: (content: string) => void
  readOnly?: boolean
}

export function CollaborativeEditor({
  docId,
  content = '',
  onContentChange,
  readOnly = false,
}: CollaborativeEditorProps) {
  const [editorContent, setEditorContent] = useState(content)
  const [hasLocalLock, setHasLocalLock] = useState(false)
  const heartbeatIntervalRef = useRef<NodeJS.Timeout>()
  const presenceIntervalRef = useRef<NodeJS.Timeout>()

  // Check document lock status
  const { data: lockStatus } = useQuery<DocumentLock>({
    queryKey: ['doc-lock', docId],
    queryFn: async () => {
      // TODO: Replace with actual API call
      // const response = await fetch(`/api/v1/docs/${docId}/lock`)
      // return await response.json()

      // Mock data - randomly lock document
      const isLocked = Math.random() > 0.7
      return {
        is_locked: isLocked,
        locked_by_user_id: isLocked ? 'user_2' : undefined,
        locked_by_user_name: isLocked ? 'Sarah Chen' : undefined,
        locked_at: isLocked ? new Date(Date.now() - 5 * 60 * 1000).toISOString() : undefined,
      }
    },
    refetchInterval: 5000, // Check lock status every 5 seconds
  })

  // Get active editors (presence)
  const { data: activeEditors = [] } = useQuery<ActiveEditor[]>({
    queryKey: ['doc-presence', docId],
    queryFn: async () => {
      // TODO: Replace with actual API call
      // const response = await fetch(`/api/v1/docs/${docId}/presence`)
      // return await response.json()

      // Mock data
      return [
        {
          user_id: 'user_3',
          user_name: 'Mike Rodriguez',
          last_seen: new Date().toISOString(),
          is_editing: false,
        },
        {
          user_id: 'user_4',
          user_name: 'Emily Johnson',
          last_seen: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
          is_editing: false,
        },
      ]
    },
    refetchInterval: 5000, // Update presence every 5 seconds
  })

  // Acquire lock mutation
  const acquireLockMutation = useMutation({
    mutationFn: async () => {
      // TODO: Replace with actual API call
      // const response = await fetch(`/api/v1/docs/${docId}/lock`, {
      //   method: 'POST',
      //   body: JSON.stringify({ user_id: 'current_user' })
      // })
      // return await response.json()
      await new Promise(resolve => setTimeout(resolve, 500))
      return { success: true }
    },
    onSuccess: (data) => {
      if (data.success) {
        setHasLocalLock(true)
        startHeartbeat()
        toast.success('Document locked for editing')
      }
    },
    onError: () => {
      toast.error('Failed to acquire lock')
    },
  })

  // Release lock mutation
  const releaseLockMutation = useMutation({
    mutationFn: async () => {
      // TODO: Replace with actual API call
      // await fetch(`/api/v1/docs/${docId}/lock`, {
      //   method: 'DELETE'
      // })
      await new Promise(resolve => setTimeout(resolve, 500))
    },
    onSuccess: () => {
      setHasLocalLock(false)
      stopHeartbeat()
    },
  })

  // Start heartbeat to keep lock alive
  function startHeartbeat() {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current)
    }

    heartbeatIntervalRef.current = setInterval(async () => {
      try {
        // TODO: Replace with actual API call
        // await fetch(`/api/v1/docs/${docId}/heartbeat`, { method: 'POST' })
      } catch (err) {
        console.error('Heartbeat failed:', err)
        toast.error('Lost connection to server')
      }
    }, 10000) // Send heartbeat every 10 seconds
  }

  // Stop heartbeat
  function stopHeartbeat() {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current)
      heartbeatIntervalRef.current = undefined
    }
  }

  // Update presence
  function updatePresence() {
    if (presenceIntervalRef.current) {
      clearInterval(presenceIntervalRef.current)
    }

    presenceIntervalRef.current = setInterval(async () => {
      try {
        // TODO: Replace with actual API call
        // await fetch(`/api/v1/docs/${docId}/presence`, { method: 'POST' })
      } catch (err) {
        console.error('Presence update failed:', err)
      }
    }, 5000) // Update presence every 5 seconds
  }

  // Try to acquire lock on mount
  useEffect(() => {
    if (!readOnly && !lockStatus?.is_locked) {
      acquireLockMutation.mutate()
    }

    updatePresence()

    return () => {
      // Release lock and stop intervals on unmount
      if (hasLocalLock) {
        releaseLockMutation.mutate()
      }
      stopHeartbeat()
      if (presenceIntervalRef.current) {
        clearInterval(presenceIntervalRef.current)
      }
    }
  }, [docId])

  function handleContentChange(newContent: string) {
    setEditorContent(newContent)
    onContentChange?.(newContent)
  }

  function formatTimeAgo(dateString: string) {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)

    if (diffMins < 1) return 'just now'
    if (diffMins < 60) return `${diffMins}m ago`
    const diffHours = Math.floor(diffMs / 3600000)
    if (diffHours < 24) return `${diffHours}h ago`
    return date.toLocaleDateString()
  }

  const isDocumentLocked = lockStatus?.is_locked && !hasLocalLock
  const showReadOnlyWarning = isDocumentLocked || readOnly

  return (
    <div className="flex flex-col h-full">
      {/* Presence Indicators */}
      {activeEditors.length > 0 && (
        <div className="px-4 py-2 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-200 dark:border-blue-800">
          <div className="flex items-center gap-3">
            <Users className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            <div className="flex flex-wrap items-center gap-2">
              {activeEditors.map((editor) => (
                <div
                  key={editor.user_id}
                  className="inline-flex items-center gap-1.5 px-2 py-1 bg-white dark:bg-blue-900/40 rounded-full text-xs border border-blue-200 dark:border-blue-700"
                >
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span className="font-medium text-blue-900 dark:text-blue-100">
                    {editor.user_name}
                  </span>
                  {editor.is_editing ? (
                    <Edit3 className="w-3 h-3 text-blue-600 dark:text-blue-400" />
                  ) : (
                    <Eye className="w-3 h-3 text-gray-500 dark:text-gray-400" />
                  )}
                  <span className="text-gray-600 dark:text-gray-400">
                    {formatTimeAgo(editor.last_seen)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Read-Only Warning */}
      {showReadOnlyWarning && lockStatus?.is_locked && (
        <div className="px-4 py-3 bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800">
          <div className="flex items-start gap-2">
            {readOnly ? (
              <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
            ) : (
              <Lock className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
            )}
            <div>
              <p className="text-sm font-medium text-amber-900 dark:text-amber-100">
                {readOnly ? 'Read-Only Mode' : 'Document Locked'}
              </p>
              {lockStatus.locked_by_user_name && (
                <p className="text-xs text-amber-700 dark:text-amber-300 mt-0.5">
                  <strong>{lockStatus.locked_by_user_name}</strong> is currently editing this
                  document. You can view but not edit.
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Lock Status Badge */}
      {hasLocalLock && (
        <div className="px-4 py-2 bg-green-50 dark:bg-green-900/20 border-b border-green-200 dark:border-green-800">
          <div className="flex items-center gap-2 text-sm text-green-800 dark:text-green-300">
            <Edit3 className="w-4 h-4" />
            <span className="font-medium">You have edit access</span>
            <button
              onClick={() => releaseLockMutation.mutate()}
              className="ml-auto text-xs text-green-600 dark:text-green-400 hover:underline"
            >
              Release lock
            </button>
          </div>
        </div>
      )}

      {/* Editor */}
      <div className="flex-1 overflow-auto">
        <textarea
          value={editorContent}
          onChange={(e) => handleContentChange(e.target.value)}
          disabled={showReadOnlyWarning}
          className="w-full h-full px-6 py-4 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100
                   font-mono text-sm resize-none focus:outline-none
                   disabled:opacity-60 disabled:cursor-not-allowed"
          placeholder={
            showReadOnlyWarning
              ? 'Document is locked by another user...'
              : 'Start typing...'
          }
        />
      </div>
    </div>
  )
}

/**
 * Presence Badge Component
 *
 * Small badge showing online user presence
 */
interface PresenceBadgeProps {
  editors: ActiveEditor[]
  maxDisplay?: number
}

export function PresenceBadge({ editors, maxDisplay = 3 }: PresenceBadgeProps) {
  const displayEditors = editors.slice(0, maxDisplay)
  const remainingCount = Math.max(0, editors.length - maxDisplay)

  if (editors.length === 0) return null

  return (
    <div className="flex items-center gap-1">
      {displayEditors.map((editor, index) => (
        <div
          key={editor.user_id}
          className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center text-xs font-medium text-blue-600 dark:text-blue-400 border-2 border-white dark:border-gray-800"
          style={{ marginLeft: index > 0 ? '-8px' : '0' }}
          title={`${editor.user_name} is ${editor.is_editing ? 'editing' : 'viewing'}`}
        >
          {editor.user_name.charAt(0)}
        </div>
      ))}
      {remainingCount > 0 && (
        <div
          className="w-8 h-8 bg-gray-200 dark:bg-gray-700 rounded-full flex items-center justify-center text-xs font-medium text-gray-600 dark:text-gray-400 border-2 border-white dark:border-gray-800"
          style={{ marginLeft: '-8px' }}
          title={`${remainingCount} more`}
        >
          +{remainingCount}
        </div>
      )}
    </div>
  )
}
