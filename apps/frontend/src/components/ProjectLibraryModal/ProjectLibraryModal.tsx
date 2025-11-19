/**
 * ProjectLibraryModal Component
 *
 * Modal for managing project documents - view, create, edit, delete, upload, download
 */

import { useState, useRef, useEffect } from 'react'
import { X, Search, Plus, Upload, FolderDown } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import JSZip from 'jszip'
import { api } from '@/lib/api'

// Components
import { DocumentRow } from './DocumentRow'
import { NewDocumentEditor } from './NewDocumentEditor'
import { EditDocumentEditor } from './EditDocumentEditor'
import { DeleteConfirmDialog } from './DeleteConfirmDialog'

// Types
import type { ProjectDocument } from './types'

export interface ProjectLibraryModalProps {
  isOpen: boolean
  onClose: () => void
  onLoadDocument?: (doc: ProjectDocument) => void
}

export function ProjectLibraryModal({
  isOpen,
  onClose,
  onLoadDocument,
}: ProjectLibraryModalProps) {
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  // State
  const [searchQuery, setSearchQuery] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [renamingId, setRenamingId] = useState<number | null>(null)
  const [newName, setNewName] = useState('')
  const [showNewEditor, setShowNewEditor] = useState(false)
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null)
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

  // Data fetching
  const { data: documents, isLoading } = useQuery({
    queryKey: ['project-documents'],
    queryFn: async () => {
      const res = await api.get('/code/library')
      return res.data as ProjectDocument[]
    },
    enabled: isOpen,
  })

  // Mutations
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

  // Handlers
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

  const handleDownloadDocument = (doc: ProjectDocument) => {
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
  }

  // Filter documents
  const filteredDocuments =
    documents?.filter(
      (doc) =>
        doc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        doc.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
        doc.tags.some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()))
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
                  {searchQuery
                    ? 'No documents found'
                    : 'No documents yet. Click "+ New" to create one.'}
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
                    onDownload={() => handleDownloadDocument(doc)}
                  />
                ))
              )}
            </div>
          )}
        </div>

        {/* Delete Confirmation Dialog */}
        {deleteConfirmId && (
          <DeleteConfirmDialog
            documentName={documents?.find((d) => d.id === deleteConfirmId)?.name || ''}
            onConfirm={() => deleteMutation.mutate(deleteConfirmId)}
            onCancel={() => setDeleteConfirmId(null)}
          />
        )}
      </div>
    </div>
  )
}
