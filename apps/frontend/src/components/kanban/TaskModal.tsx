import { useState, useEffect } from 'react'
import { X, Send } from 'lucide-react'
import toast from 'react-hot-toast'
import * as kanbanApi from '@/lib/kanbanApi'
import type { TaskItem, CommentItem } from '@/lib/kanbanApi'

interface TaskModalProps {
  taskId: string
  onClose: () => void
  onUpdate: (task: TaskItem) => void
}

export function TaskModal({ taskId, onClose, onUpdate }: TaskModalProps) {
  const [task, setTask] = useState<TaskItem | null>(null)
  const [comments, setComments] = useState<CommentItem[]>([])
  const [newComment, setNewComment] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadTaskAndComments()
  }, [taskId])

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

  const loadTaskAndComments = async () => {
    try {
      // Find task from parent
      setLoading(false)
      const commentsData = await kanbanApi.listComments(taskId)
      setComments(commentsData)
    } catch (err) {
      toast.error('Failed to load task details')
    }
  }

  const handleAddComment = async () => {
    if (!newComment.trim()) return

    try {
      const comment = await kanbanApi.createComment(taskId, newComment)
      setComments([...comments, comment])
      setNewComment('')
      toast.success('Comment added')
    } catch (err) {
      toast.error('Failed to add comment')
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Task Details</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Title
            </label>
            <input
              type="text"
              className="w-full px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg"
              placeholder="Task title"
              disabled
            />
          </div>

          {/* Comments Section */}
          <div className="mt-8">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Comments ({comments.length})
            </h3>

            <div className="space-y-3 mb-4">
              {comments.map(comment => (
                <div key={comment.comment_id} className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
                  <p className="text-sm text-gray-900 dark:text-gray-100">{comment.content}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {new Date(comment.created_at).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>

            {/* Add Comment */}
            <div className="flex gap-2">
              <input
                type="text"
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddComment()}
                placeholder="Add a comment..."
                className="flex-1 px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg"
              />
              <button
                onClick={handleAddComment}
                className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg flex items-center gap-2"
              >
                <Send size={16} />
                Send
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
