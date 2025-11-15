import { useState, useEffect, useRef } from 'react'
import { DragDropContext, DropResult } from '@hello-pangea/dnd'
import toast from 'react-hot-toast'
import { Plus, BookOpen, Wifi, WifiOff } from 'lucide-react'
import * as Y from 'yjs'
import * as kanbanApi from '@/lib/kanbanApi'
import type { ProjectItem, BoardItem, ColumnItem, TaskItem } from '@/lib/kanbanApi'
import { BoardColumns } from '@/components/kanban/BoardColumns'
import { TaskModal } from '@/components/kanban/TaskModal'
import { ProjectWiki } from '@/components/kanban/ProjectWiki'
import { createProviders } from '@/lib/collab/yProvider'
import { applyMoveAndGetHints } from '@/lib/collab/yArrayOps'

export default function KanbanWorkspace() {
  const [projects, setProjects] = useState<ProjectItem[]>([])
  const [boards, setBoards] = useState<BoardItem[]>([])
  const [columns, setColumns] = useState<ColumnItem[]>([])
  const [tasksDict, setTasksDict] = useState<Record<string, TaskItem>>({})
  const [tasksByColumn, setTasksByColumn] = useState<Record<string, TaskItem[]>>({})

  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)
  const [selectedBoardId, setSelectedBoardId] = useState<string | null>(null)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [connected, setConnected] = useState(false)

  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const [isWikiOpen, setIsWikiOpen] = useState(false)

  // Yjs refs
  const ydocRef = useRef<Y.Doc | null>(null)
  const yColumnsRef = useRef<Y.Map<Y.Array<string>> | null>(null)
  const providerRef = useRef<any>(null)

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

  // Load columns and tasks with Yjs when board changes
  useEffect(() => {
    if (!selectedBoardId) {
      // Cleanup on board deselect
      if (providerRef.current) {
        providerRef.current.destroy?.()
        providerRef.current = null
      }
      if (ydocRef.current) {
        ydocRef.current.destroy()
        ydocRef.current = null
      }
      yColumnsRef.current = null
      setColumns([])
      setTasksDict({})
      setTasksByColumn({})
      return
    }

    let cancelled = false

    async function loadBoardWithYjs() {
      try {
        // Fetch REST data
        const [columnsData, tasksData] = await Promise.all([
          kanbanApi.listColumns(selectedBoardId!),
          kanbanApi.listTasks(selectedBoardId!)
        ])

        if (cancelled) return

        setColumns(columnsData)

        // Build tasks dictionary
        const dict: Record<string, TaskItem> = {}
        for (const t of tasksData) {
          dict[t.task_id] = t
        }
        setTasksDict(dict)

        // Initialize Yjs
        const ydoc = new Y.Doc()
        ydocRef.current = ydoc

        const providers = createProviders(`board:${selectedBoardId}`, ydoc)
        providerRef.current = providers

        // Monitor connection status
        providers.wsProvider.on('status', (event: { status: string }) => {
          setConnected(event.status === 'connected')
        })

        const yColumns = ydoc.getMap<Y.Array<string>>('columns')
        yColumnsRef.current = yColumns

        // Seed Y.Doc from REST if empty
        const isEmpty = yColumns.size === 0
        if (isEmpty) {
          columnsData.forEach(col => {
            const arr = new Y.Array<string>()
            const colTasks = tasksData
              .filter(t => t.column_id === col.column_id)
              .sort((a, b) => a.position - b.position)
              .map(t => t.task_id)
            arr.insert(0, colTasks)
            yColumns.set(col.column_id, arr)
          })
        }

        // Subscribe to Y.Doc updates to rebuild tasksByColumn
        const rebuild = () => {
          const map: Record<string, TaskItem[]> = {}
          for (const c of columnsData) {
            const arr = yColumns.get(c.column_id)
            const ids = arr ? arr.toArray() : []
            map[c.column_id] = ids.map(id => dict[id]).filter(Boolean)
          }
          setTasksByColumn(map)
        }

        ydoc.on('update', rebuild)
        rebuild() // Initial build
      } catch (err) {
        if (!cancelled) {
          toast.error('Failed to load board data')
        }
      }
    }

    loadBoardWithYjs()

    return () => {
      cancelled = true
      // Cleanup on board change or unmount
      if (providerRef.current) {
        providerRef.current.destroy?.()
        providerRef.current = null
      }
      if (ydocRef.current) {
        ydocRef.current.destroy()
        ydocRef.current = null
      }
      yColumnsRef.current = null
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
      }
    } catch (err) {
      toast.error('Failed to load boards')
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

      // Add empty array to Yjs
      if (yColumnsRef.current) {
        const arr = new Y.Array<string>()
        yColumnsRef.current.set(column.column_id, arr)
      }

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

      // Update tasks dict
      setTasksDict(prev => ({ ...prev, [task.task_id]: task }))

      // Add to Yjs column array
      if (yColumnsRef.current) {
        const arr = yColumnsRef.current.get(columnId)
        if (arr) {
          arr.push([task.task_id])
        }
      }

      toast.success('Task created')
    } catch (err) {
      toast.error('Failed to create task')
    }
  }

  const handleDragEnd = async (result: DropResult) => {
    const { destination, source, draggableId } = result

    if (!destination) return
    if (destination.droppableId === source.droppableId && destination.index === source.index) return
    if (!yColumnsRef.current) return

    const taskId = draggableId
    const fromColumnId = source.droppableId
    const toColumnId = destination.droppableId
    const fromIndex = source.index
    const toIndex = destination.index

    const yColumns = yColumnsRef.current

    // Apply optimistic move and get neighbor hints
    const { rollback, hints } = applyMoveAndGetHints(yColumns, {
      taskId,
      fromColumnId,
      toColumnId,
      fromIndex,
      toIndex
    })

    // Persist to backend
    try {
      const updatedTask = await kanbanApi.updateTask(taskId, {
        column_id: toColumnId,
        before_task_id: hints.before_task_id,
        after_task_id: hints.after_task_id
      })

      // Update tasks dict with server position
      setTasksDict(prev => ({ ...prev, [taskId]: updatedTask }))
    } catch (err) {
      // Revert optimistic change
      rollback()
      toast.error('Failed to move task')
    }
  }

  const handleTaskClick = (taskId: string) => {
    setSelectedTaskId(taskId)
  }

  const handleTaskUpdate = (updatedTask: TaskItem) => {
    setTasksDict(prev => ({ ...prev, [updatedTask.task_id]: updatedTask }))
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

            {/* Connection status */}
            {selectedBoardId && (
              <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                {connected ? (
                  <>
                    <Wifi size={14} className="text-green-500" />
                    <span>Live</span>
                  </>
                ) : (
                  <>
                    <WifiOff size={14} className="text-gray-400" />
                    <span>Offline</span>
                  </>
                )}
              </div>
            )}
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
              tasks={Object.values(tasksByColumn).flat()}
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
