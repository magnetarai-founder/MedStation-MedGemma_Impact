/**
 * Code Editor API Client
 */

const API_BASE = '/api/v1/code-editor'

export interface Workspace {
  id: string
  name: string
  source_type: 'disk' | 'database'
  disk_path?: string
  created_at: string
  updated_at: string
}

export interface CodeFile {
  id: string
  workspace_id: string
  name: string
  path: string
  content: string
  language: string
  created_at: string
  updated_at: string
}

export interface FileTreeNode {
  id: string
  name: string
  path: string
  is_directory: boolean
  children?: FileTreeNode[]
}

export const codeEditorApi = {
  // Workspaces
  async createWorkspace(data: {
    name: string
    source_type: 'database'
  }): Promise<Workspace> {
    const res = await fetch(`${API_BASE}/workspaces`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })

    if (!res.ok) {
      const error = await res.json()
      throw new Error(error.detail || 'Failed to create workspace')
    }

    return res.json()
  },

  async openDiskWorkspace(name: string, diskPath: string): Promise<Workspace> {
    const formData = new FormData()
    formData.append('name', name)
    formData.append('disk_path', diskPath)

    const res = await fetch(`${API_BASE}/workspaces/open-disk`, {
      method: 'POST',
      body: formData,
    })

    if (!res.ok) {
      const error = await res.json()
      throw new Error(error.detail || 'Failed to open workspace')
    }

    return res.json()
  },

  async openDatabaseWorkspace(workspaceId: string): Promise<Workspace> {
    const formData = new FormData()
    formData.append('workspace_id', workspaceId)

    const res = await fetch(`${API_BASE}/workspaces/open-database`, {
      method: 'POST',
      body: formData,
    })

    if (!res.ok) {
      const error = await res.json()
      throw new Error(error.detail || 'Failed to open workspace')
    }

    return res.json()
  },

  async listWorkspaces(): Promise<Workspace[]> {
    const res = await fetch(`${API_BASE}/workspaces`)
    if (!res.ok) throw new Error('Failed to fetch workspaces')
    const data = await res.json()
    return data.workspaces
  },

  async getWorkspaceFiles(workspaceId: string): Promise<FileTreeNode[]> {
    const res = await fetch(`${API_BASE}/workspaces/${workspaceId}/files`)
    if (!res.ok) throw new Error('Failed to fetch files')
    const data = await res.json()
    return data.files
  },

  async syncWorkspace(workspaceId: string): Promise<{ success: boolean; files_synced: number }> {
    const res = await fetch(`${API_BASE}/workspaces/${workspaceId}/sync`, {
      method: 'POST',
    })
    if (!res.ok) throw new Error('Failed to sync workspace')
    return res.json()
  },

  // Files
  async getFile(fileId: string): Promise<CodeFile> {
    const res = await fetch(`${API_BASE}/files/${fileId}`)
    if (!res.ok) throw new Error('Failed to fetch file')
    return res.json()
  },

  async createFile(file: {
    workspace_id: string
    name: string
    path: string
    content: string
    language: string
  }): Promise<CodeFile> {
    const res = await fetch(`${API_BASE}/files`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(file),
    })

    if (!res.ok) {
      const error = await res.json()
      throw new Error(error.detail || 'Failed to create file')
    }

    return res.json()
  },

  async updateFile(
    fileId: string,
    updates: {
      name?: string
      path?: string
      content?: string
      language?: string
    }
  ): Promise<CodeFile> {
    const res = await fetch(`${API_BASE}/files/${fileId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    })

    if (!res.ok) {
      const error = await res.json()
      throw new Error(error.detail || 'Failed to update file')
    }

    return res.json()
  },

  async deleteFile(fileId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/files/${fileId}`, {
      method: 'DELETE',
    })

    if (!res.ok) {
      const error = await res.json()
      throw new Error(error.detail || 'Failed to delete file')
    }
  },

  async importFile(workspaceId: string, file: File): Promise<CodeFile> {
    const formData = new FormData()
    formData.append('workspace_id', workspaceId)
    formData.append('file', file)

    const res = await fetch(`${API_BASE}/files/import`, {
      method: 'POST',
      body: formData,
    })

    if (!res.ok) {
      const error = await res.json()
      throw new Error(error.detail || 'Failed to import file')
    }

    return res.json()
  },
}
