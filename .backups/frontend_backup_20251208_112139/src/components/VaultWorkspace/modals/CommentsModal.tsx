import { useState, useEffect } from 'react'
import { MessageSquare, X, Send } from 'lucide-react'
import axios from 'axios'
import toast from 'react-hot-toast'

interface CommentsModalProps {
  isOpen: boolean
  file: any
  vaultMode: string
  onClose: () => void
}

export function CommentsModal({ isOpen, file, vaultMode, onClose }: CommentsModalProps) {
  const [fileComments, setFileComments] = useState<Array<any>>([])
  const [newComment, setNewComment] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(false)

  useEffect(() => {
    if (isOpen && file) {
      // Reset pagination when modal opens
      setFileComments([])
      setOffset(0)
      setHasMore(false)
      loadFileComments(0)
    }
  }, [isOpen, file])

  // Handle Escape key to close modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [onClose])

  const loadFileComments = async (currentOffset: number = offset) => {
    if (!file) return

    const isInitialLoad = currentOffset === 0
    if (isInitialLoad) {
      setIsLoading(true)
    } else {
      setIsLoadingMore(true)
    }

    try {
      const response = await axios.get(`/api/v1/vault/files/${file.id}/comments`, {
        params: {
          vault_type: vaultMode,
          limit: 50,
          offset: currentOffset
        }
      })

      const newComments = response.data.comments || []
      setFileComments(prev => currentOffset === 0 ? newComments : [...prev, ...newComments])
      setOffset(currentOffset + newComments.length)
      setHasMore(response.data.has_more || false)
    } catch (error) {
      console.error('Failed to load comments:', error)
      toast.error('Failed to load comments')
    } finally {
      setIsLoading(false)
      setIsLoadingMore(false)
    }
  }

  const handleLoadMore = () => {
    loadFileComments(offset)
  }

  const handleAddComment = async () => {
    if (!newComment.trim() || !file) return

    try {
      const formData = new FormData()
      formData.append('vault_type', vaultMode)
      formData.append('comment_text', newComment.trim())

      await axios.post(`/api/v1/vault/files/${file.id}/comments`, formData)
      toast.success('Comment added')
      setNewComment('')
      // Reset pagination and reload
      setFileComments([])
      setOffset(0)
      setHasMore(false)
      loadFileComments(0)
    } catch (error) {
      console.error('Add comment failed:', error)
      toast.error('Failed to add comment')
    }
  }

  const handleDeleteComment = async (commentId: string) => {
    if (!confirm('Delete this comment?')) return

    try {
      await axios.delete(`/api/v1/vault/comments/${commentId}`, {
        params: { vault_type: vaultMode }
      })
      toast.success('Comment deleted')
      // Reset pagination and reload
      setFileComments([])
      setOffset(0)
      setHasMore(false)
      loadFileComments(0)
    } catch (error) {
      console.error('Delete comment failed:', error)
      toast.error('Failed to delete comment')
    }
  }

  if (!isOpen || !file) return null

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded-lg w-[600px] max-h-[80vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-300 dark:border-zinc-700">
          <h3 className="text-lg font-semibold flex items-center gap-2 text-gray-900 dark:text-gray-100">
            <MessageSquare className="w-5 h-5" />
            Comments - "{file.filename}"
          </h3>
          <button onClick={onClose}>
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Comments List */}
        <div className="flex-1 overflow-y-auto p-4">
          {isLoading ? (
            <div className="text-center py-12 text-gray-500 dark:text-zinc-500">
              <MessageSquare className="w-16 h-16 mx-auto mb-4 opacity-20 animate-pulse" />
              <p>Loading comments...</p>
            </div>
          ) : fileComments.length === 0 ? (
            <div className="text-center py-12 text-gray-500 dark:text-zinc-500">
              <MessageSquare className="w-16 h-16 mx-auto mb-4 opacity-20" />
              <p>No comments yet</p>
            </div>
          ) : (
            <div className="space-y-3">
              {fileComments.map((comment) => (
                <div
                  key={comment.id}
                  className="p-3 bg-gray-100 dark:bg-zinc-800 rounded border border-gray-300 dark:border-zinc-700"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <p className="text-gray-900 dark:text-gray-100">{comment.comment_text}</p>
                      <p className="text-xs text-gray-500 dark:text-zinc-600 mt-1">
                        {new Date(comment.created_at).toLocaleString()}
                        {comment.updated_at && ' (edited)'}
                      </p>
                    </div>
                    <button
                      onClick={() => handleDeleteComment(comment.id)}
                      className="p-1 hover:bg-red-100 dark:hover:bg-red-900/20 rounded text-red-600 dark:text-red-400"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}

              {/* Load More Button */}
              {hasMore && (
                <div className="flex justify-center pt-2">
                  <button
                    onClick={handleLoadMore}
                    disabled={isLoadingMore}
                    className="px-4 py-2 bg-gray-200 dark:bg-zinc-700 hover:bg-gray-300 dark:hover:bg-zinc-600 disabled:opacity-50 disabled:cursor-not-allowed text-gray-900 dark:text-gray-100 rounded text-sm"
                  >
                    {isLoadingMore ? 'Loading...' : 'Load More'}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Add Comment Input */}
        <div className="p-4 border-t border-gray-300 dark:border-zinc-700">
          <div className="flex gap-2">
            <input
              type="text"
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleAddComment()}
              placeholder="Add a comment..."
              className="flex-1 px-3 py-2 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded text-gray-900 dark:text-gray-100"
            />
            <button
              onClick={handleAddComment}
              disabled={!newComment.trim()}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded flex items-center gap-2"
            >
              <Send className="w-4 h-4" />
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
