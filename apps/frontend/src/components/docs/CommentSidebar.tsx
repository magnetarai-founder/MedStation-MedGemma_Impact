/**
 * Comment Sidebar Component
 *
 * Sidebar panel displaying all comments for a document
 * Supports filtering (show resolved), adding new comments, and real-time updates
 */

import { useState, useEffect } from 'react'
import { MessageSquare, Plus, Filter, X } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { CommentThread } from './CommentThread'

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

interface CommentSidebarProps {
  docId: string
  isOpen?: boolean
  onClose?: () => void
}

export function CommentSidebar({ docId, isOpen = true, onClose }: CommentSidebarProps) {
  const [showResolved, setShowResolved] = useState(false)
  const [isAddingComment, setIsAddingComment] = useState(false)
  const [newCommentText, setNewCommentText] = useState('')
  const [replyingTo, setReplyingTo] = useState<string | null>(null)
  const queryClient = useQueryClient()

  // Fetch comments
  const { data: comments = [], isLoading } = useQuery({
    queryKey: ['doc-comments', docId],
    queryFn: async () => {
      // TODO: Replace with actual API call
      // const response = await fetch(`/api/v1/docs/${docId}/comments`)
      // const data = await response.json()
      // return data.comments as Comment[]

      // Mock data for now
      return [
        {
          comment_id: '1',
          doc_id: docId,
          user_id: 'user_1',
          user_name: 'Field Worker',
          comment_text: 'This section needs more detail about the implementation approach.',
          selection_range: { start: 10, end: 25 },
          created_at: new Date().toISOString(),
          resolved: false,
          replies: [
            {
              comment_id: '2',
              doc_id: docId,
              user_id: 'user_2',
              user_name: 'Sarah Chen',
              comment_text: 'Agreed. I can add more context about the technical requirements.',
              parent_comment_id: '1',
              created_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
              resolved: false,
            },
          ],
        },
        {
          comment_id: '3',
          doc_id: docId,
          user_id: 'user_3',
          user_name: 'Mike Rodriguez',
          comment_text: 'Great summary! This is exactly what we needed.',
          created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
          resolved: true,
        },
        {
          comment_id: '4',
          doc_id: docId,
          user_id: 'user_1',
          user_name: 'Field Worker',
          comment_text: 'Should we include cost estimates here?',
          selection_range: { start: 50, end: 75 },
          created_at: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
          resolved: false,
        },
      ] as Comment[]
    },
    refetchInterval: 10000, // Poll for updates every 10 seconds
  })

  // Create comment mutation
  const createCommentMutation = useMutation({
    mutationFn: async ({ text, parentId }: { text: string; parentId?: string }) => {
      // TODO: Replace with actual API call
      // await fetch(`/api/v1/docs/${docId}/comments`, {
      //   method: 'POST',
      //   body: JSON.stringify({
      //     text,
      //     parent_id: parentId,
      //     user_id: 'current_user'
      //   })
      // })
      await new Promise(resolve => setTimeout(resolve, 500))
      return { text, parentId }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['doc-comments', docId] })
      toast.success('Comment added')
      setNewCommentText('')
      setIsAddingComment(false)
      setReplyingTo(null)
    },
    onError: () => {
      toast.error('Failed to add comment')
    },
  })

  function handleAddComment() {
    if (!newCommentText.trim()) {
      toast.error('Comment cannot be empty')
      return
    }
    createCommentMutation.mutate({
      text: newCommentText,
      parentId: replyingTo || undefined,
    })
  }

  function handleReply(commentId: string) {
    setReplyingTo(commentId)
    setIsAddingComment(true)
  }

  function handleCancelComment() {
    setIsAddingComment(false)
    setNewCommentText('')
    setReplyingTo(null)
  }

  // Build comment tree (nest replies under parent comments)
  function buildCommentTree(comments: Comment[]): Comment[] {
    const commentMap = new Map<string, Comment>()
    const rootComments: Comment[] = []

    // First pass: create map of all comments
    comments.forEach(comment => {
      commentMap.set(comment.comment_id, { ...comment, replies: [] })
    })

    // Second pass: build tree structure
    comments.forEach(comment => {
      const commentWithReplies = commentMap.get(comment.comment_id)!
      if (comment.parent_comment_id) {
        const parent = commentMap.get(comment.parent_comment_id)
        if (parent) {
          parent.replies = parent.replies || []
          parent.replies.push(commentWithReplies)
        } else {
          // Parent not found, treat as root comment
          rootComments.push(commentWithReplies)
        }
      } else {
        rootComments.push(commentWithReplies)
      }
    })

    return rootComments
  }

  const commentTree = buildCommentTree(comments)
  const filteredComments = showResolved
    ? commentTree
    : commentTree.filter(c => !c.resolved)

  if (!isOpen) return null

  return (
    <aside className="w-80 h-full bg-gray-50 dark:bg-gray-900 border-l border-gray-200 dark:border-gray-700 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            <h3 className="font-semibold text-gray-900 dark:text-gray-100">
              Comments
            </h3>
            <span className="px-2 py-0.5 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full text-xs font-medium">
              {comments.length}
            </span>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
              aria-label="Close comments"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Filter Toggle */}
        <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 cursor-pointer">
          <input
            type="checkbox"
            checked={showResolved}
            onChange={(e) => setShowResolved(e.target.checked)}
            className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
          />
          <Filter className="w-3 h-3" />
          Show resolved
        </label>
      </div>

      {/* Comments List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          </div>
        ) : filteredComments.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">
              {showResolved
                ? 'No comments yet'
                : 'No unresolved comments'}
            </p>
            <p className="text-xs mt-1">
              {!showResolved && comments.length > 0
                ? `${comments.length} resolved ${comments.length === 1 ? 'comment' : 'comments'}`
                : 'Start a conversation by adding a comment'}
            </p>
          </div>
        ) : (
          filteredComments.map((comment) => (
            <CommentThread
              key={comment.comment_id}
              comment={comment}
              onReply={handleReply}
            />
          ))
        )}
      </div>

      {/* Add Comment Form */}
      {isAddingComment ? (
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          {replyingTo && (
            <div className="mb-2 text-xs text-gray-600 dark:text-gray-400">
              Replying to comment...
            </div>
          )}
          <textarea
            value={newCommentText}
            onChange={(e) => setNewCommentText(e.target.value)}
            placeholder="Write your comment..."
            className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none mb-2"
            rows={3}
            autoFocus
          />
          <div className="flex items-center gap-2">
            <button
              onClick={handleAddComment}
              disabled={createCommentMutation.isPending}
              className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors disabled:opacity-50 flex-1"
            >
              {createCommentMutation.isPending ? 'Adding...' : 'Add Comment'}
            </button>
            <button
              onClick={handleCancelComment}
              className="px-3 py-1.5 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-200 text-sm rounded-lg transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={() => setIsAddingComment(true)}
            className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Add Comment
          </button>
        </div>
      )}
    </aside>
  )
}
