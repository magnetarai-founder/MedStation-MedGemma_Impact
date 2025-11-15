import type { TaskItem } from '@/lib/kanbanApi'
import { Tag, AlertCircle } from 'lucide-react'

interface TaskCardProps {
  task: TaskItem
  onClick: () => void
  isDragging: boolean
}

export function TaskCard({ task, onClick, isDragging }: TaskCardProps) {
  const priorityColors = {
    high: 'text-red-600 dark:text-red-400',
    medium: 'text-yellow-600 dark:text-yellow-400',
    low: 'text-green-600 dark:text-green-400'
  }

  return (
    <div
      onClick={onClick}
      className={`p-3 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg cursor-pointer hover:shadow-md transition-shadow ${
        isDragging ? 'shadow-lg opacity-50' : ''
      }`}
    >
      <div className="flex items-start justify-between mb-2">
        <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 flex-1">
          {task.title}
        </h4>
        {task.priority && (
          <AlertCircle
            size={14}
            className={priorityColors[task.priority as keyof typeof priorityColors] || 'text-gray-400'}
          />
        )}
      </div>

      {task.description && (
        <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 line-clamp-2">
          {task.description}
        </p>
      )}

      {task.tags && task.tags.length > 0 && (
        <div className="flex items-center gap-1 flex-wrap">
          {task.tags.map((tag, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1 px-2 py-0.5 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded text-xs"
            >
              <Tag size={10} />
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
