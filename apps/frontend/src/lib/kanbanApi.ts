import { api } from './api'

const BASE = '/api/v1/kanban'

// ===== Types =====
export interface ProjectItem {
  project_id: string
  name: string
  description: string | null
  created_at: string
}

export interface BoardItem {
  board_id: string
  project_id: string
  name: string
  created_at: string
}

export interface ColumnItem {
  column_id: string
  board_id: string
  name: string
  position: number
}

export interface TaskItem {
  task_id: string
  board_id: string
  column_id: string
  title: string
  description: string | null
  status: string | null
  assignee_id: string | null
  priority: string | null
  due_date: string | null
  tags: string[]
  position: number
  created_at: string
  updated_at: string
}

export interface CommentItem {
  comment_id: string
  task_id: string
  user_id: string
  content: string
  created_at: string
}

export interface WikiItem {
  page_id: string
  project_id: string
  title: string
  content: string | null
  created_at: string
  updated_at: string
}

// ===== Projects =====
export async function listProjects(): Promise<ProjectItem[]> {
  const response = await api.get(`${BASE}/projects`)
  return response.data
}

export async function createProject(
  name: string,
  description?: string
): Promise<ProjectItem> {
  const response = await api.post(`${BASE}/projects`, { name, description })
  return response.data
}

// ===== Boards =====
export async function listBoards(projectId: string): Promise<BoardItem[]> {
  const response = await api.get(`${BASE}/projects/${projectId}/boards`)
  return response.data
}

export async function createBoard(
  projectId: string,
  name: string
): Promise<BoardItem> {
  const response = await api.post(`${BASE}/boards`, { project_id: projectId, name })
  return response.data
}

// ===== Columns =====
export async function listColumns(boardId: string): Promise<ColumnItem[]> {
  const response = await api.get(`${BASE}/boards/${boardId}/columns`)
  return response.data
}

export async function createColumn(
  boardId: string,
  name: string,
  position?: number
): Promise<ColumnItem> {
  const response = await api.post(`${BASE}/columns`, { board_id: boardId, name, position })
  return response.data
}

export async function updateColumn(
  columnId: string,
  updates: { name?: string; position?: number }
): Promise<ColumnItem> {
  const response = await api.patch(`${BASE}/columns/${columnId}`, updates)
  return response.data
}

// ===== Tasks =====
export async function listTasks(
  boardId: string,
  columnId?: string
): Promise<TaskItem[]> {
  const params = columnId ? { column_id: columnId } : {}
  const response = await api.get(`${BASE}/boards/${boardId}/tasks`, { params })
  return response.data
}

export interface CreateTaskData {
  board_id: string
  column_id: string
  title: string
  description?: string
  status?: string
  assignee_id?: string
  priority?: string
  due_date?: string
  tags?: string[]
  position?: number
}

export async function createTask(data: CreateTaskData): Promise<TaskItem> {
  const response = await api.post(`${BASE}/tasks`, data)
  return response.data
}

export interface UpdateTaskData {
  title?: string
  description?: string
  status?: string
  assignee_id?: string
  priority?: string
  due_date?: string
  tags?: string[]
  column_id?: string
  position?: number
  before_task_id?: string
  after_task_id?: string
}

export async function updateTask(
  taskId: string,
  updates: UpdateTaskData
): Promise<TaskItem> {
  const response = await api.patch(`${BASE}/tasks/${taskId}`, updates)
  return response.data
}

// ===== Comments =====
export async function listComments(taskId: string): Promise<CommentItem[]> {
  const response = await api.get(`${BASE}/tasks/${taskId}/comments`)
  return response.data
}

export async function createComment(
  taskId: string,
  content: string
): Promise<CommentItem> {
  const response = await api.post(`${BASE}/comments`, { task_id: taskId, content })
  return response.data
}

// ===== Wiki =====
export async function listWiki(projectId: string): Promise<WikiItem[]> {
  const response = await api.get(`${BASE}/projects/${projectId}/wiki`)
  return response.data
}

export async function createWiki(
  projectId: string,
  title: string,
  content?: string
): Promise<WikiItem> {
  const response = await api.post(`${BASE}/wiki`, { project_id: projectId, title, content })
  return response.data
}

export async function updateWiki(
  pageId: string,
  updates: { title?: string; content?: string }
): Promise<WikiItem> {
  const response = await api.patch(`${BASE}/wiki/${pageId}`, updates)
  return response.data
}
