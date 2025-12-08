import { Droppable, Draggable } from '@hello-pangea/dnd'
import { Plus } from 'lucide-react'
import type { ColumnItem, TaskItem } from '@/lib/kanbanApi'
import { TaskCard } from './TaskCard'

interface ColumnProps {
  column: ColumnItem
  tasks: TaskItem[]
  onTaskClick: (taskId: string) => void
  onCreateTask: (columnId: string) => void
}

export function Column({ column, tasks, onTaskClick, onCreateTask }: ColumnProps) {
  return (
    <div className="flex-1 min-w-80 bg-gray-800/50 dark:bg-gray-800/50 rounded-lg border border-gray-700/50 dark:border-gray-700 flex flex-col max-h-full">
      {/* Column Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <h3 className="font-semibold text-gray-900 dark:text-gray-100">
          {column.name}
          <span className="ml-2 text-sm text-gray-500 dark:text-gray-400">
            ({tasks.length})
          </span>
        </h3>
        <button
          onClick={() => onCreateTask(column.column_id)}
          className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          title="Add Task"
        >
          <Plus size={18} />
        </button>
      </div>

      {/* Task List */}
      <Droppable droppableId={column.column_id}>
        {(provided, snapshot) => (
          <div
            ref={provided.innerRef}
            {...provided.droppableProps}
            className={`flex-1 overflow-y-auto p-2 space-y-2 ${
              snapshot.isDraggingOver ? 'bg-primary-50 dark:bg-primary-900/20' : ''
            }`}
            style={{ minHeight: '100px' }}
          >
            {tasks.map((task, index) => (
              <Draggable key={task.task_id} draggableId={task.task_id} index={index}>
                {(provided, snapshot) => (
                  <div
                    ref={provided.innerRef}
                    {...provided.draggableProps}
                    {...provided.dragHandleProps}
                    style={provided.draggableProps.style}
                  >
                    <TaskCard
                      task={task}
                      onClick={() => onTaskClick(task.task_id)}
                      isDragging={snapshot.isDragging}
                    />
                  </div>
                )}
              </Draggable>
            ))}
            {provided.placeholder}
          </div>
        )}
      </Droppable>
    </div>
  )
}
