/**
 * Comment Thread Component
 *
 * Displays a comment and its threaded replies
 * Supports resolve/unresolve, reply, and edit actions
 */

import { useState } from 'react'
import { MessageSquare, Check, Reply, MoreVertical, Trash2, Edit2, User } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'

interface Comment {
  comment_id: string
  doc_id: string
  user_id: string
  user_name: string
  comment_text: string
  selection_range?: { start: number; end: number }
  parent_comment_id?: string
  created_at: string
  resolved: boolean
  replies?: Comment[]
}

interface CommentThreadProps {
  comment: Comment
  onReply?: (commentId: string) => void
  onResolve?: (commentId: string) => void
  onDelete?: (commentId: string) => void
}

export function CommentThread({ comment, onReply, onResolve, onDelete }: CommentThreadProps) {
  const [showMenu, setShowMenu] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [editText, setEditText] = useState(comment.comment_text)
  const queryClient = useQueryClient()

  // Resolve comment mutation
  const resolveMutation = useMutation({
    mutationFn: async (commentId: string) => {
      // TODO: Replace with actual API call
      // await fetch(`/api/v1/docs/${comment.doc_id}/comments/${commentId}/resolve`, {
      //   method: 'POST'
      // })
      await new Promise(resolve => setTimeout(resolve, 500))
      return commentId
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['doc-comments', comment.doc_id] })
      toast.success(comment.resolved ? 'Comment reopened' : 'Comment resolved')
      onResolve?.(comment.comment_id)
    },
    onError: () => {
      toast.error('Failed to update comment')
    },
  })

  // Delete comment mutation
  const deleteMutation = useMutation({
    mutationFn: async (commentId: string) => {
      // TODO: Replace with actual API call
      // await fetch(`/api/v1/docs/${comment.doc_id}/comments/${commentId}`, {
      //   method: 'DELETE'
      // })
      await new Promise(resolve => setTimeout(resolve, 500))
      return commentId
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['doc-comments', comment.doc_id] })
      toast.success('Comment deleted')
      onDelete?.(comment.comment_id)
    },
    onError: () => {
      toast.error('Failed to delete comment')
    },
  })

  // Update comment mutation
  const updateMutation = useMutation({
    mutationFn: async ({ commentId, text }: { commentId: string; text: string }) => {
      // TODO: Replace with actual API call
      // await fetch(`/api/v1/docs/${comment.doc_id}/comments/${commentId}`, {
      //   method: 'PUT',
      //   body: JSON.stringify({ text })
      // })
      await new Promise(resolve => setTimeout(resolve, 500))
      return { commentId, text }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['doc-comments', comment.doc_id] })
      toast.success('Comment updated')
      setIsEditing(false)
    },
    onError: () => {
      toast.error('Failed to update comment')
    },
  })

  function handleResolve() {
    resolveMutation.mutate(comment.comment_id)
    setShowMenu(false)
  }

  function handleDelete() {
    if (!confirm('Delete this comment? This cannot be undone.')) {
      return
    }
    deleteMutation.mutate(comment.comment_id)
    setShowMenu(false)
  }

  function handleSaveEdit() {
    if (!editText.trim()) {
      toast.error('Comment cannot be empty')
      return
    }
    updateMutation.mutate({ commentId: comment.comment_id, text: editText })
  }

  function handleCancelEdit() {
    setIsEditing(false)
    setEditText(comment.comment_text)
  }

  function formatTimeAgo(dateString: string) {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  return (
    <div className={`space-y-2 ${comment.resolved ? 'opacity-60' : ''}`}>
      <div
        className={`p-3 rounded-lg border ${
          comment.resolved
            ? 'bg-gray-50 dark:bg-gray-800/50 border-gray-200 dark:border-gray-700'
            : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-600'
        }`}
      >
        {/* Comment Header */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center">
              <User className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                {comment.user_name}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {formatTimeAgo(comment.created_at)}
              </div>
            </div>
          </div>

          <div className="relative">
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
              aria-label="Comment options"
            >
              <MoreVertical className="w-4 h-4" />
            </button>

            {showMenu && (
              <div className="absolute right-0 top-full mt-1 w-40 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-10">
                <button
                  onClick={() => {
                    setIsEditing(true)
                    setShowMenu(false)
                  }}
                  className="w-full px-3 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2"
                >
                  <Edit2 className="w-3 h-3" />
                  Edit
                </button>
                <button
                  onClick={handleResolve}
                  disabled={resolveMutation.isPending}
                  className="w-full px-3 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2"
                >
                  <Check className="w-3 h-3" />
                  {comment.resolved ? 'Unresolve' : 'Resolve'}
                </button>
                <button
                  onClick={handleDelete}
                  disabled={deleteMutation.isPending}
                  className="w-full px-3 py-2 text-left text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-2 rounded-b-lg"
                >
                  <Trash2 className="w-3 h-3" />
                  Delete
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Selection Range Badge */}
        {comment.selection_range && (
          <div className="mb-2">
            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded text-xs">
              <MessageSquare className="w-3 h-3" />
              Lines {comment.selection_range.start}-{comment.selection_range.end}
            </span>
          </div>
        )}

        {/* Comment Text or Edit Form */}
        {isEditing ? (
          <div className="space-y-2">
            <textarea
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              rows={3}
            />
            <div className="flex items-center gap-2">
              <button
                onClick={handleSaveEdit}
                disabled={updateMutation.isPending}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors disabled:opacity-50"
              >
                {updateMutation.isPending ? 'Saving...' : 'Save'}
              </button>
              <button
                onClick={handleCancelEdit}
                className="px-3 py-1.5 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-200 text-sm rounded-lg transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <>
            <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
              {comment.comment_text}
            </p>

            {/* Resolved Badge */}
            {comment.resolved && (
              <div className="mt-2">
                <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded text-xs font-medium">
                  <Check className="w-3 h-3" />
                  Resolved
                </span>
              </div>
            )}

            {/* Reply Button */}
            {!comment.resolved && (
              <button
                onClick={() => onReply?.(comment.comment_id)}
                className="mt-2 inline-flex items-center gap-1 px-2 py-1 text-xs text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors"
              >
                <Reply className="w-3 h-3" />
                Reply
              </button>
            )}
          </>
        )}
      </div>

      {/* Threaded Replies */}
      {comment.replies && comment.replies.length > 0 && (
        <div className="ml-6 space-y-2 border-l-2 border-gray-200 dark:border-gray-700 pl-3">
          {comment.replies.map((reply) => (
            <CommentThread
              key={reply.comment_id}
              comment={reply}
              onReply={onReply}
              onResolve={onResolve}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}
    </div>
  )
}
