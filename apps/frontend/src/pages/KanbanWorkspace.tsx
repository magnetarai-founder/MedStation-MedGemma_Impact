import { useState, useEffect } from 'react'
import { DragDropContext, DropResult } from '@hello-pangea/dnd'
import toast from 'react-hot-toast'
import { Plus, BookOpen } from 'lucide-react'
import * as kanbanApi from '@/lib/kanbanApi'
import type { ProjectItem, BoardItem, ColumnItem, TaskItem } from '@/lib/kanbanApi'
import { BoardColumns } from '@/components/kanban/BoardColumns'
import { TaskModal } from '@/components/kanban/TaskModal'
import { ProjectWiki } from '@/components/kanban/ProjectWiki'

export default function KanbanWorkspace() {
  const [projects, setProjects] = useState<ProjectItem[]>([])
  const [boards, setBoards] = useState<BoardItem[]>([])
  const [columns, setColumns] = useState<ColumnItem[]>([])
  const [tasks, setTasks] = useState<TaskItem[]>([])

  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)
  const [selectedBoardId, setSelectedBoardId] = useState<string | null>(null)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const [isWikiOpen, setIsWikiOpen] = useState(false)

  // Load projects on mount
  useEffect(() => {
    loadProjects()
  }, [])

  // Load boards when project changes
  useEffect(() => {
    if (selectedProjectId) {
      loadBoards(selectedProjectId)
    }
  }, [selectedProjectId])

  // Load columns and tasks when board changes
  useEffect(() => {
    if (selectedBoardId) {
      loadColumnsAndTasks(selectedBoardId)
    }
  }, [selectedBoardId])

  const loadProjects = async () => {
    try {
      setLoading(true)
      const data = await kanbanApi.listProjects()
      setProjects(data)

      // Auto-select first project if available
      if (data.length > 0 && !selectedProjectId) {
        setSelectedProjectId(data[0].project_id)
      }
    } catch (err) {
      setError('Failed to load projects')
      toast.error('Failed to load projects')
    } finally {
      setLoading(false)
    }
  }

  const loadBoards = async (projectId: string) => {
    try {
      const data = await kanbanApi.listBoards(projectId)
      setBoards(data)

      // Auto-select first board if available
      if (data.length > 0) {
        setSelectedBoardId(data[0].board_id)
      } else {
        setSelectedBoardId(null)
        setColumns([])
        setTasks([])
      }
    } catch (err) {
      toast.error('Failed to load boards')
    }
  }

  const loadColumnsAndTasks = async (boardId: string) => {
    try {
      const [columnsData, tasksData] = await Promise.all([
        kanbanApi.listColumns(boardId),
        kanbanApi.listTasks(boardId)
      ])
      setColumns(columnsData)
      setTasks(tasksData)
    } catch (err) {
      toast.error('Failed to load board data')
    }
  }

  const handleCreateProject = async () => {
    const name = prompt('Project name:')
    if (!name) return

    try {
      const project = await kanbanApi.createProject(name)
      setProjects([...projects, project])
      setSelectedProjectId(project.project_id)
      toast.success('Project created')
    } catch (err) {
      toast.error('Failed to create project')
    }
  }

  const handleCreateBoard = async () => {
    if (!selectedProjectId) {
      toast.error('Please select a project first')
      return
    }

    const name = prompt('Board name:')
    if (!name) return

    try {
      const board = await kanbanApi.createBoard(selectedProjectId, name)
      setBoards([...boards, board])
      setSelectedBoardId(board.board_id)
      toast.success('Board created')
    } catch (err) {
      toast.error('Failed to create board')
    }
  }

  const handleCreateColumn = async () => {
    if (!selectedBoardId) {
      toast.error('Please select a board first')
      return
    }

    const name = prompt('Column name:')
    if (!name) return

    try {
      const column = await kanbanApi.createColumn(selectedBoardId, name)
      setColumns([...columns, column])
      toast.success('Column created')
    } catch (err) {
      toast.error('Failed to create column')
    }
  }

  const handleCreateTask = async (columnId: string) => {
    if (!selectedBoardId) return

    const title = prompt('Task title:')
    if (!title) return

    try {
      const task = await kanbanApi.createTask({
        board_id: selectedBoardId,
        column_id: columnId,
        title
      })
      setTasks([...tasks, task])
      toast.success('Task created')
    } catch (err) {
      toast.error('Failed to create task')
    }
  }

  const handleDragEnd = async (result: DropResult) => {
    const { destination, source, draggableId } = result

    if (!destination) return
    if (destination.droppableId === source.droppableId && destination.index === source.index) return

    const taskId = draggableId
    const srcColumnId = source.droppableId
    const dstColumnId = destination.droppableId

    // Optimistic update
    const task = tasks.find(t => t.task_id === taskId)
    if (!task) return

    const previousTasks = [...tasks]

    // Remove from source
    let updatedTasks = tasks.filter(t => t.task_id !== taskId)

    // Get tasks in destination column
    const dstTasks = updatedTasks.filter(t => t.column_id === dstColumnId)

    // Insert at destination index
    const before = dstTasks[destination.index - 1]
    const after = dstTasks[destination.index]

    // Update task object optimistically
    const updatedTask = { ...task, column_id: dstColumnId }
    updatedTasks.splice(
      updatedTasks.findIndex(t => t.column_id === dstColumnId && t.position > (before?.position || 0)) || updatedTasks.length,
      0,
      updatedTask
    )

    setTasks(updatedTasks)

    // Persist to backend
    try {
      const persistedTask = await kanbanApi.updateTask(taskId, {
        column_id: dstColumnId,
        before_task_id: before?.task_id,
        after_task_id: after?.task_id
      })

      // Update with server position
      setTasks(prev => prev.map(t => t.task_id === taskId ? persistedTask : t))
    } catch (err) {
      // Revert on error
      setTasks(previousTasks)
      toast.error('Failed to move task')
    }
  }

  const handleTaskClick = (taskId: string) => {
    setSelectedTaskId(taskId)
  }

  const handleTaskUpdate = (updatedTask: TaskItem) => {
    setTasks(prev => prev.map(t => t.task_id === updatedTask.task_id ? updatedTask : t))
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-gray-600 dark:text-gray-400">Loading...</div>
      </div>
    )
  }

  if (projects.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-900 p-8">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
          No Projects Yet
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mb-6 text-center max-w-md">
          Create your first project to start organizing tasks with kanban boards.
        </p>
        <button
          onClick={handleCreateProject}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg flex items-center gap-2"
        >
          <Plus size={18} />
          Create Project
        </button>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <select
              value={selectedProjectId || ''}
              onChange={(e) => setSelectedProjectId(e.target.value)}
              className="px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg text-sm"
            >
              {projects.map(p => (
                <option key={p.project_id} value={p.project_id}>{p.name}</option>
              ))}
            </select>

            <select
              value={selectedBoardId || ''}
              onChange={(e) => setSelectedBoardId(e.target.value)}
              className="px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg text-sm"
              disabled={boards.length === 0}
            >
              {boards.length === 0 ? (
                <option value="">No boards</option>
              ) : (
                boards.map(b => (
                  <option key={b.board_id} value={b.board_id}>{b.name}</option>
                ))
              )}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCreateProject}
              className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              New Project
            </button>
            <button
              onClick={handleCreateBoard}
              className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
              disabled={!selectedProjectId}
            >
              New Board
            </button>
            <button
              onClick={handleCreateColumn}
              className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
              disabled={!selectedBoardId}
            >
              New Column
            </button>
            <button
              onClick={() => setIsWikiOpen(true)}
              className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center gap-2"
              disabled={!selectedProjectId}
            >
              <BookOpen size={16} />
              Wiki
            </button>
          </div>
        </div>
      </div>

      {/* Board Content */}
      <div className="flex-1 overflow-auto p-6">
        {!selectedBoardId ? (
          <div className="text-center text-gray-600 dark:text-gray-400 mt-12">
            {boards.length === 0 ? 'No boards in this project. Create one to get started.' : 'Select a board to view'}
          </div>
        ) : (
          <DragDropContext onDragEnd={handleDragEnd}>
            <BoardColumns
              columns={columns}
              tasks={tasks}
              onTaskClick={handleTaskClick}
              onCreateTask={handleCreateTask}
            />
          </DragDropContext>
        )}
      </div>

      {/* Task Modal */}
      {selectedTaskId && (
        <TaskModal
          taskId={selectedTaskId}
          onClose={() => setSelectedTaskId(null)}
          onUpdate={handleTaskUpdate}
        />
      )}

      {/* Wiki Modal */}
      {isWikiOpen && selectedProjectId && (
        <ProjectWiki
          projectId={selectedProjectId}
          onClose={() => setIsWikiOpen(false)}
        />
      )}
    </div>
  )
}
