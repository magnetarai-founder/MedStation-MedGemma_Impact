import { useState, useEffect } from 'react'
import { MessageSquare, X, Send } from 'lucide-react'
import axios from 'axios'
import { toast } from 'sonner'

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

  useEffect(() => {
    if (isOpen && file) {
      loadFileComments()
    }
  }, [isOpen, file])

  const loadFileComments = async () => {
    if (!file) return

    setIsLoading(true)
    try {
      const response = await axios.get(`/api/v1/vault/files/${file.id}/comments`, {
        params: { vault_type: vaultMode }
      })
      setFileComments(response.data.comments)
    } catch (error) {
      console.error('Failed to load comments:', error)
      toast.error('Failed to load comments')
    } finally {
      setIsLoading(false)
    }
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
      loadFileComments()
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
      loadFileComments()
    } catch (error) {
      console.error('Delete comment failed:', error)
      toast.error('Failed to delete comment')
    }
  }

  if (!isOpen || !file) return null

  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-zinc-900 border border-gray-300 dark:border-zinc-700 rounded-lg w-[600px] max-h-[80vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
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
