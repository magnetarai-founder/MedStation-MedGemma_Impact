import { useState, useRef, useEffect } from 'react'
import { X, Search, Plus, Edit2, ArrowRight, MoreVertical, Trash2, Upload, Download, FolderDown, Hash } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Editor from '@monaco-editor/react'
import JSZip from 'jszip'
import { api } from '../lib/api'

interface ProjectDocument {
  id: number
  name: string
  content: string
  tags: string[]
  file_type: 'markdown' | 'text'
  created_at: string
  updated_at: string
}

interface ProjectLibraryModalProps {
  isOpen: boolean
  onClose: () => void
  onLoadDocument?: (doc: ProjectDocument) => void
}

export function ProjectLibraryModal({ isOpen, onClose, onLoadDocument }: ProjectLibraryModalProps) {
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [renamingId, setRenamingId] = useState<number | null>(null)
  const [newName, setNewName] = useState('')
  const [showNewEditor, setShowNewEditor] = useState(false)
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploadedDoc, setUploadedDoc] = useState<{ name: string; content: string } | null>(null)

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

  const { data: documents, isLoading } = useQuery({
    queryKey: ['project-documents'],
    queryFn: async () => {
      const res = await api.get('/code/library')
      return res.data as ProjectDocument[]
    },
    enabled: isOpen,
  })

  const renameMutation = useMutation({
    mutationFn: async ({ id, name }: { id: number; name: string }) => {
      await api.patch(`/code/library/${id}`, { name })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-documents'] })
      setRenamingId(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/code/library/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-documents'] })
      setDeleteConfirmId(null)
    },
  })

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files || files.length === 0) return

    const file = files[0]
    const ext = file.name.split('.').pop()?.toLowerCase()

    if (ext !== 'md' && ext !== 'txt') {
      alert('Only .md and .txt files are supported')
      event.target.value = ''
      return
    }

    const content = await file.text()
    const name = file.name.replace(/\.(md|txt)$/, '')

    setUploadedDoc({ name, content })
    setShowNewEditor(true)
    event.target.value = ''
  }

  const handleBulkExport = async () => {
    if (!documents || documents.length === 0) {
      alert('No documents to export')
      return
    }

    try {
      const zip = new JSZip()

      documents.forEach((doc) => {
        const ext = doc.file_type === 'markdown' ? 'md' : 'txt'
        zip.file(`${doc.name}.${ext}`, doc.content)
      })

      const blob = await zip.generateAsync({ type: 'blob' })
      const now = new Date()
      const timestamp = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`

      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `project_library_${timestamp}.zip`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to create bulk export:', error)
      alert('Failed to export documents')
    }
  }

  const filteredDocuments = documents?.filter((doc) =>
    doc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    doc.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
    doc.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
  ) || []

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />

      {/* Modal */}
      <div className="relative w-full max-w-5xl max-h-[85vh] bg-white dark:bg-gray-900 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-4 flex-1">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              Project Library
            </h2>
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search documents and tags..."
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
              disabled={!documents || documents.length === 0}
              className={`px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg flex items-center space-x-2 ${
                documents && documents.length > 0
                  ? 'hover:bg-gray-100 dark:hover:bg-gray-800'
                  : 'opacity-50 cursor-not-allowed'
              }`}
              title="Bulk export all documents as .zip"
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

            <input
              ref={fileInputRef}
              type="file"
              accept=".md,.txt"
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
          {/* New Document Editor */}
          {showNewEditor && (
            <NewDocumentEditor
              initialData={uploadedDoc}
              onClose={() => {
                setShowNewEditor(false)
                setUploadedDoc(null)
              }}
              onSave={() => {
                setShowNewEditor(false)
                setUploadedDoc(null)
              }}
            />
          )}

          {/* Edit Document Editor */}
          {editingId && (
            <EditDocumentEditor
              documentId={editingId}
              onClose={() => setEditingId(null)}
              onSave={() => setEditingId(null)}
            />
          )}

          {/* Document List */}
          {!showNewEditor && !editingId && (
            <div className="space-y-2">
              {isLoading ? (
                <div className="text-center py-8 text-gray-500">Loading...</div>
              ) : filteredDocuments.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  {searchQuery ? 'No documents found' : 'No documents yet. Click "+ New" to create one.'}
                </div>
              ) : (
                filteredDocuments.map((doc) => (
                  <DocumentRow
                    key={doc.id}
                    document={doc}
                    isRenaming={renamingId === doc.id}
                    newName={newName}
                    onStartRename={() => {
                      setRenamingId(doc.id)
                      setNewName(doc.name)
                    }}
                    onNameChange={setNewName}
                    onSaveRename={() => {
                      if (newName.trim() && newName !== doc.name) {
                        renameMutation.mutate({ id: doc.id, name: newName.trim() })
                      } else {
                        setRenamingId(null)
                      }
                    }}
                    onCancelRename={() => setRenamingId(null)}
                    onEdit={() => setEditingId(doc.id)}
                    onLoad={() => onLoadDocument?.(doc)}
                    onDelete={() => setDeleteConfirmId(doc.id)}
                    onDownload={() => {
                      const ext = doc.file_type === 'markdown' ? 'md' : 'txt'
                      const blob = new Blob([doc.content], { type: 'text/plain' })
                      const url = URL.createObjectURL(blob)
                      const a = document.createElement('a')
                      a.href = url
                      a.download = `${doc.name}.${ext}`
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
            documentName={documents?.find(d => d.id === deleteConfirmId)?.name || ''}
            onConfirm={() => deleteMutation.mutate(deleteConfirmId)}
            onCancel={() => setDeleteConfirmId(null)}
          />
        )}
      </div>
    </div>
  )
}

interface DocumentRowProps {
  document: ProjectDocument
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

function DocumentRow({
  document,
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
}: DocumentRowProps) {
  const [showMenu, setShowMenu] = useState(false)

  return (
    <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors group">
      {/* Left: Download icon + Name + Tags */}
      <div className="flex items-center space-x-2 flex-1">
        <button
          onClick={onDownload}
          className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-600 opacity-0 group-hover:opacity-100 transition-opacity"
          title="Download file"
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
              {document.name}
            </h4>
          )}
          <div className="flex items-center gap-2 mt-1">
            {/* Tags as pills */}
            {document.tags.map((tag, idx) => (
              <span
                key={idx}
                className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400"
              >
                #{tag}
              </span>
            ))}
            {document.tags.length === 0 && (
              <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-1">
                {document.content.slice(0, 100)}...
              </p>
            )}
          </div>
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

interface TagInputProps {
  tags: string[]
  onChange: (tags: string[]) => void
  maxTags?: number
}

function TagInput({ tags, onChange, maxTags = 3 }: TagInputProps) {
  const [inputValue, setInputValue] = useState('')
  const [hoveredTag, setHoveredTag] = useState<number | null>(null)

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && inputValue.trim()) {
      e.preventDefault()
      if (tags.length >= maxTags) {
        alert(`Maximum ${maxTags} tags allowed`)
        return
      }
      const newTag = inputValue.trim().toLowerCase().replace(/^#+/, '') // Remove leading #
      if (!tags.includes(newTag)) {
        onChange([...tags, newTag])
      }
      setInputValue('')
    }
  }

  const removeTag = (index: number) => {
    onChange(tags.filter((_, i) => i !== index))
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2 mb-2">
        {tags.map((tag, idx) => (
          <div
            key={idx}
            className="group relative inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 text-sm font-medium transition-all"
            onMouseEnter={() => setHoveredTag(idx)}
            onMouseLeave={() => setHoveredTag(null)}
          >
            <Hash className="w-3 h-3" />
            <span>{tag}</span>
            {hoveredTag === idx && (
              <button
                onClick={() => removeTag(idx)}
                className="ml-1 p-0.5 rounded-full hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors"
                title="Remove tag"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>
        ))}
      </div>
      {tags.length < maxTags && (
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`Add tag (${tags.length}/${maxTags})... Press Enter`}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 text-sm"
        />
      )}
    </div>
  )
}

function NewDocumentEditor({
  initialData,
  onClose,
  onSave
}: {
  initialData?: { name: string; content: string } | null
  onClose: () => void
  onSave: () => void
}) {
  const queryClient = useQueryClient()
  const [name, setName] = useState(initialData?.name || '')
  const [fileType, setFileType] = useState<'markdown' | 'text'>('markdown')
  const [content, setContent] = useState(initialData?.content || '')
  const [tags, setTags] = useState<string[]>([])

  const saveMutation = useMutation({
    mutationFn: async () => {
      await api.post('/code/library', {
        name: name.trim(),
        content: content.trim(),
        file_type: fileType,
        tags,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-documents'] })
      onSave()
    },
  })

  return (
    <div className="mb-6 p-6 bg-gray-50 dark:bg-gray-800 rounded-lg border-2 border-blue-500">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Create New Document
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
            placeholder="My Document"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Type
          </label>
          <div className="flex gap-4">
            <label className="flex items-center">
              <input
                type="radio"
                value="markdown"
                checked={fileType === 'markdown'}
                onChange={(e) => setFileType(e.target.value as 'markdown')}
                className="mr-2"
              />
              <span className="text-gray-900 dark:text-gray-100">Markdown (.md)</span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                value="text"
                checked={fileType === 'text'}
                onChange={(e) => setFileType(e.target.value as 'text')}
                className="mr-2"
              />
              <span className="text-gray-900 dark:text-gray-100">Text (.txt)</span>
            </label>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Tags (up to 3)
          </label>
          <TagInput tags={tags} onChange={setTags} maxTags={3} />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Content
          </label>
          <div className="border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden">
            <Editor
              height="400px"
              language={fileType === 'markdown' ? 'markdown' : 'plaintext'}
              value={content}
              onChange={(value) => setContent(value || '')}
              theme="vs-dark"
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                wordWrap: 'on',
              }}
            />
          </div>
        </div>

        <div className="flex justify-end space-x-3 pt-4">
          <button
            onClick={onClose}
            className="px-6 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            Cancel
          </button>
          <button
            onClick={() => saveMutation.mutate()}
            disabled={!name.trim() || !content.trim() || saveMutation.isPending}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {saveMutation.isPending ? 'Saving...' : 'Save Document'}
          </button>
        </div>
      </div>
    </div>
  )
}

function EditDocumentEditor({
  documentId,
  onClose,
  onSave,
}: {
  documentId: number
  onClose: () => void
  onSave: () => void
}) {
  const queryClient = useQueryClient()
  const { data: documents } = useQuery({
    queryKey: ['project-documents'],
    queryFn: async () => {
      const res = await api.get('/code/library')
      return res.data as ProjectDocument[]
    },
  })

  const document = documents?.find(d => d.id === documentId)
  const [name, setName] = useState(document?.name || '')
  const [content, setContent] = useState(document?.content || '')
  const [tags, setTags] = useState<string[]>(document?.tags || [])

  useEffect(() => {
    if (document) {
      setName(document.name)
      setContent(document.content)
      setTags(document.tags)
    }
  }, [document])

  const updateMutation = useMutation({
    mutationFn: async () => {
      await api.patch(`/code/library/${documentId}`, {
        name: name.trim(),
        content: content.trim(),
        tags,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-documents'] })
      onSave()
    },
  })

  if (!document) {
    return (
      <div className="mb-6 p-6 bg-gray-50 dark:bg-gray-800 rounded-lg border-2 border-blue-500">
        <div className="text-center text-gray-500">Loading document...</div>
      </div>
    )
  }

  return (
    <div className="mb-6 p-6 bg-gray-50 dark:bg-gray-800 rounded-lg border-2 border-blue-500">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Edit Document
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
            placeholder="My Document"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Tags (up to 3)
          </label>
          <TagInput tags={tags} onChange={setTags} maxTags={3} />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Content
          </label>
          <div className="border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden">
            <Editor
              height="400px"
              language={document.file_type === 'markdown' ? 'markdown' : 'plaintext'}
              value={content}
              onChange={(value) => setContent(value || '')}
              theme="vs-dark"
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                wordWrap: 'on',
              }}
            />
          </div>
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
            disabled={!name.trim() || !content.trim() || updateMutation.isPending}
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
  documentName,
  onConfirm,
  onCancel,
}: {
  documentName: string
  onConfirm: () => void
  onCancel: () => void
}) {
  const [confirmText, setConfirmText] = useState('')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/70" onClick={onCancel} />
      <div className="relative bg-white dark:bg-gray-900 rounded-xl p-6 max-w-md shadow-2xl">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Delete Document
        </h3>
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          You are about to delete <strong>{documentName}</strong>. This action cannot be undone.
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
