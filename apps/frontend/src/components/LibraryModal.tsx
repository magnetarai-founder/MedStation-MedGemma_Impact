import { useState, useRef, useEffect } from 'react'
import { X, Search, Plus, Edit2, ArrowRight, MoreVertical, Trash2, Upload, FileUp, Download, FolderDown } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as settingsApi from '@/lib/settingsApi'
import Editor from '@monaco-editor/react'
import JSZip from 'jszip'

interface LibraryModalProps {
  isOpen: boolean
  onClose: () => void
  onLoadQuery?: (query: settingsApi.SavedQuery) => void
  initialCodeData?: { name: string; content: string } | null
}

export function LibraryModal({ isOpen, onClose, onLoadQuery, initialCodeData }: LibraryModalProps) {
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [renamingId, setRenamingId] = useState<number | null>(null)
  const [newName, setNewName] = useState('')
  const [showNewEditor, setShowNewEditor] = useState(false)
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Handle ESC key to close modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])

  const { data: queries, isLoading } = useQuery({
    queryKey: ['saved-queries'],
    queryFn: () => settingsApi.getSavedQueries(),
  })

  const renameMutation = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) =>
      settingsApi.updateQuery(id, { name }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-queries'] })
      setRenamingId(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: settingsApi.deleteQuery,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-queries'] })
      setDeleteConfirmId(null)
    },
  })

  const uploadMutation = useMutation({
    mutationFn: async (files: { name: string; query: string; type: 'sql' | 'json' }[]) => {
      // Save all files in parallel
      await Promise.all(files.map(f => settingsApi.saveQuery(f)))
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-queries'] })
    },
  })

  const [uploadedQuery, setUploadedQuery] = useState<{ name: string; content: string } | null>(null)

  // Open editor with code from CodeEditor download button
  useEffect(() => {
    if (initialCodeData && isOpen) {
      setUploadedQuery(initialCodeData)
      setShowNewEditor(true)
    }
  }, [initialCodeData, isOpen])

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files || files.length === 0) return

    const file = files[0] // Single file only
    const ext = file.name.split('.').pop()?.toLowerCase()

    if (ext !== 'sql') {
      alert('Only .sql files are supported')
      event.target.value = ''
      return
    }

    const content = await file.text()
    const name = file.name.replace(/\.sql$/, '')

    // Set uploaded query data and open editor
    setUploadedQuery({ name, content })
    setShowNewEditor(true)

    // Reset input
    event.target.value = ''
  }

  const filteredQueries = queries?.filter((q) =>
    q.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    q.query.toLowerCase().includes(searchQuery.toLowerCase())
  ) || []

  const handleBulkExport = async () => {
    if (!queries || queries.length === 0) {
      alert('No queries to export')
      return
    }

    try {
      const zip = new JSZip()

      // Add each query as a .sql file
      queries.forEach((query) => {
        zip.file(`${query.name}.sql`, query.query)
      })

      // Generate zip file
      const blob = await zip.generateAsync({ type: 'blob' })

      // Create timestamp for folder name (YYYYMMDD_HHMMSS)
      const now = new Date()
      const timestamp = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`

      // Download the zip file
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `neutron_star_${timestamp}.zip`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to create bulk export:', error)
      alert('Failed to export queries')
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
      />

      {/* Modal */}
      <div className="relative w-full max-w-5xl max-h-[85vh] bg-white dark:bg-gray-900 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-4 flex-1">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              Library
            </h2>
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search queries..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              />
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {/* Bulk Export Button */}
            <button
              onClick={handleBulkExport}
              disabled={!queries || queries.length === 0}
              className={`px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg flex items-center space-x-2 ${
                queries && queries.length > 0
                  ? 'hover:bg-gray-100 dark:hover:bg-gray-800'
                  : 'opacity-50 cursor-not-allowed'
              }`}
              title="Bulk export all queries as .zip"
            >
              <FolderDown className="w-4 h-4" />
              <span>Bulk Export</span>
            </button>

            {/* Upload Button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 flex items-center space-x-2"
            >
              <Upload className="w-4 h-4" />
              <span>Upload</span>
            </button>

            {/* Hidden file input */}
            <input
              ref={fileInputRef}
              type="file"
              accept=".sql"
              onChange={handleFileUpload}
              className="hidden"
            />

            <button
              onClick={() => setShowNewEditor(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center space-x-2"
            >
              <Plus className="w-4 h-4" />
              <span>New</span>
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {/* Upload Progress */}
          {uploadMutation.isPending && (
            <div className="mb-4 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
              <div className="flex items-center space-x-3">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                <span className="text-blue-900 dark:text-blue-100">Uploading files...</span>
              </div>
            </div>
          )}

          {uploadMutation.isSuccess && (
            <div className="mb-4 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
              <span className="text-green-900 dark:text-green-100">✓ Files uploaded successfully!</span>
            </div>
          )}

          {/* New Query Editor */}
          {showNewEditor && (
            <NewQueryEditor
              initialData={uploadedQuery}
              onClose={() => {
                setShowNewEditor(false)
                setUploadedQuery(null)
              }}
              onSave={() => {
                setShowNewEditor(false)
                setUploadedQuery(null)
              }}
            />
          )}

          {/* Edit Query Editor */}
          {editingId && (
            <EditQueryEditor
              queryId={editingId}
              onClose={() => setEditingId(null)}
              onSave={() => {
                setEditingId(null)
              }}
            />
          )}

          {/* Query List */}
          {!showNewEditor && !editingId && (
            <div className="space-y-2">
              {isLoading ? (
                <div className="text-center py-8 text-gray-500">Loading...</div>
              ) : filteredQueries.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  {searchQuery ? 'No queries found' : 'No saved queries yet. Click "+ New" to create one.'}
                </div>
              ) : (
                filteredQueries.map((query) => (
                  <QueryRow
                    key={query.id}
                    query={query}
                    isRenaming={renamingId === query.id}
                    newName={newName}
                    onStartRename={() => {
                      setRenamingId(query.id)
                      setNewName(query.name)
                    }}
                    onNameChange={setNewName}
                    onSaveRename={() => {
                      if (newName.trim() && newName !== query.name) {
                        renameMutation.mutate({ id: query.id, name: newName.trim() })
                      } else {
                        setRenamingId(null)
                      }
                    }}
                    onCancelRename={() => setRenamingId(null)}
                    onEdit={() => setEditingId(query.id)}
                    onLoad={() => onLoadQuery?.(query)}
                    onDelete={() => setDeleteConfirmId(query.id)}
                    onDownload={() => {
                      // Download single query as name.sql
                      const blob = new Blob([query.query], { type: 'text/plain' })
                      const url = URL.createObjectURL(blob)
                      const a = document.createElement('a')
                      a.href = url
                      a.download = `${query.name}.sql`
                      document.body.appendChild(a)
                      a.click()
                      document.body.removeChild(a)
                      URL.revokeObjectURL(url)
                    }}
                  />
                ))
              )}
            </div>
          )}
        </div>

        {/* Delete Confirmation Dialog */}
        {deleteConfirmId && (
          <DeleteConfirmDialog
            queryName={queries?.find(q => q.id === deleteConfirmId)?.name || ''}
            onConfirm={() => deleteMutation.mutate(deleteConfirmId)}
            onCancel={() => setDeleteConfirmId(null)}
          />
        )}
      </div>
    </div>
  )
}

interface QueryRowProps {
  query: settingsApi.SavedQuery
  isRenaming: boolean
  newName: string
  onStartRename: () => void
  onNameChange: (name: string) => void
  onSaveRename: () => void
  onCancelRename: () => void
  onEdit: () => void
  onLoad: () => void
  onDelete: () => void
  onDownload: () => void
}

function QueryRow({
  query,
  isRenaming,
  newName,
  onStartRename,
  onNameChange,
  onSaveRename,
  onCancelRename,
  onEdit,
  onLoad,
  onDelete,
  onDownload,
}: QueryRowProps) {
  const [showMenu, setShowMenu] = useState(false)

  return (
    <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors group">
      {/* Left: Download icon + Name */}
      <div className="flex items-center space-x-2 flex-1">
        <button
          onClick={onDownload}
          className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-600 opacity-0 group-hover:opacity-100 transition-opacity"
          title="Download as .sql"
        >
          <Download className="w-4 h-4 text-gray-600 dark:text-gray-300" />
        </button>
        <div className="flex-1">
        {isRenaming ? (
          <input
            type="text"
            value={newName}
            onChange={(e) => onNameChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') onSaveRename()
              if (e.key === 'Escape') onCancelRename()
            }}
            onBlur={onSaveRename}
            autoFocus
            className="px-2 py-1 border border-blue-500 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
          />
        ) : (
          <h4
            className="font-medium text-gray-900 dark:text-gray-100 cursor-text"
            onDoubleClick={onStartRename}
          >
            {query.name}
          </h4>
        )}
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 line-clamp-1">
            {query.query}
          </p>
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center space-x-2 ml-4">
        <button
          onClick={onEdit}
          className="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-600 opacity-0 group-hover:opacity-100 transition-opacity"
          title="Edit"
        >
          <Edit2 className="w-4 h-4 text-gray-600 dark:text-gray-300" />
        </button>
        <button
          onClick={onLoad}
          className="p-2 rounded hover:bg-blue-100 dark:hover:bg-blue-900 opacity-0 group-hover:opacity-100 transition-opacity"
          title="Load to editor"
        >
          <ArrowRight className="w-4 h-4 text-blue-600 dark:text-blue-400" />
        </button>
        <div className="relative">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="p-2 rounded hover:bg-gray-200 dark:hover:bg-gray-600 opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <MoreVertical className="w-4 h-4 text-gray-600 dark:text-gray-300" />
          </button>
          {showMenu && (
            <div className="absolute right-0 mt-2 w-32 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-10">
              <button
                onClick={() => {
                  onDelete()
                  setShowMenu(false)
                }}
                className="w-full px-4 py-2 text-left text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg flex items-center space-x-2"
              >
                <Trash2 className="w-4 h-4" />
                <span>Delete</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function NewQueryEditor({
  initialData,
  onClose,
  onSave
}: {
  initialData?: { name: string; content: string } | null;
  onClose: () => void;
  onSave: () => void
}) {
  const queryClient = useQueryClient()
  const [name, setName] = useState(initialData?.name || '')
  const [type, setType] = useState<'sql' | 'json'>('sql')
  const [code, setCode] = useState(initialData?.content || '')
  const [description, setDescription] = useState('')

  const saveMutation = useMutation({
    mutationFn: settingsApi.saveQuery,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-queries'] })
      onSave()
    },
  })

  return (
    <div className="mb-6 p-6 bg-gray-50 dark:bg-gray-800 rounded-lg border-2 border-blue-500">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Create New Query
        </h3>
        <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="My Query"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Query
          </label>
          <div className="border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden">
            <Editor
              height="300px"
              language={type === 'sql' ? 'sql' : 'json'}
              value={code}
              onChange={(value) => setCode(value || '')}
              theme="vs-dark"
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
              }}
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Description (Optional)
          </label>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What does this query do?"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
          />
        </div>

        <div className="flex justify-end space-x-3 pt-4">
          <button
            onClick={onClose}
            className="px-6 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            Cancel
          </button>
          <button
            onClick={() =>
              saveMutation.mutate({
                name: name.trim(),
                query: code.trim(),
                query_type: type,
                description: description.trim() || undefined,
              })
            }
            disabled={!name.trim() || !code.trim() || saveMutation.isPending}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {saveMutation.isPending ? 'Saving...' : 'Save Query'}
          </button>
        </div>
      </div>
    </div>
  )
}

function EditQueryEditor({
  queryId,
  onClose,
  onSave,
}: {
  queryId: number
  onClose: () => void
  onSave: () => void
}) {
  const queryClient = useQueryClient()
  const { data: queries } = useQuery({
    queryKey: ['saved-queries'],
    queryFn: () => settingsApi.getSavedQueries(),
  })

  const query = queries?.find(q => q.id === queryId)
  const [name, setName] = useState(query?.name || '')
  const [code, setCode] = useState(query?.query || '')
  const [description, setDescription] = useState(query?.description || '')

  // Update state when query loads
  useEffect(() => {
    if (query) {
      setName(query.name)
      setCode(query.query)
      setDescription(query.description || '')
    }
  }, [query])

  const updateMutation = useMutation({
    mutationFn: () => settingsApi.updateQuery(queryId, {
      name: name.trim(),
      query: code.trim(),
      description: description.trim() || undefined,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-queries'] })
      onSave()
    },
  })

  if (!query) {
    return (
      <div className="mb-6 p-6 bg-gray-50 dark:bg-gray-800 rounded-lg border-2 border-blue-500">
        <div className="text-center text-gray-500">Loading query...</div>
      </div>
    )
  }

  return (
    <div className="mb-6 p-6 bg-gray-50 dark:bg-gray-800 rounded-lg border-2 border-blue-500">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Edit Query
        </h3>
        <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="My Query"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Query
          </label>
          <div className="border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden">
            <Editor
              height="300px"
              language="sql"
              value={code}
              onChange={(value) => setCode(value || '')}
              theme="vs-dark"
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
              }}
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Description (Optional)
          </label>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What does this query do?"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
          />
        </div>

        <div className="flex justify-end space-x-3 pt-4">
          <button
            onClick={onClose}
            className="px-6 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            Cancel
          </button>
          <button
            onClick={() => updateMutation.mutate()}
            disabled={!name.trim() || !code.trim() || updateMutation.isPending}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  )
}

function DeleteConfirmDialog({
  queryName,
  onConfirm,
  onCancel,
}: {
  queryName: string
  onConfirm: () => void
  onCancel: () => void
}) {
  const [confirmText, setConfirmText] = useState('')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/70" onClick={onCancel} />
      <div className="relative bg-white dark:bg-gray-900 rounded-xl p-6 max-w-md shadow-2xl">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Delete Query
        </h3>
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          You are about to delete <strong>{queryName}</strong>. This action cannot be undone.
        </p>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          Type <strong>DELETE</strong> to confirm:
        </p>
        <input
          type="text"
          value={confirmText}
          onChange={(e) => setConfirmText(e.target.value)}
          placeholder="DELETE"
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 mb-4"
        />
        <div className="flex justify-end space-x-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={confirmText !== 'DELETE'}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  )
}
