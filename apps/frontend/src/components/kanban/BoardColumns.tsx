import type { ColumnItem, TaskItem } from '@/lib/kanbanApi'
import { Column } from './Column'

interface BoardColumnsProps {
  columns: ColumnItem[]
  tasks: TaskItem[]
  onTaskClick: (taskId: string) => void
  onCreateTask: (columnId: string) => void
}

export function BoardColumns({ columns, tasks, onTaskClick, onCreateTask }: BoardColumnsProps) {
  // Group tasks by column
  const tasksByColumn: Record<string, TaskItem[]> = {}
  columns.forEach(col => {
    tasksByColumn[col.column_id] = tasks
      .filter(t => t.column_id === col.column_id)
      .sort((a, b) => a.position - b.position)
  })

  return (
    <div className="flex gap-4 h-full w-full">
      {columns.map(column => (
        <Column
          key={column.column_id}
          column={column}
          tasks={tasksByColumn[column.column_id] || []}
          onTaskClick={onTaskClick}
          onCreateTask={onCreateTask}
        />
      ))}
    </div>
  )
}
