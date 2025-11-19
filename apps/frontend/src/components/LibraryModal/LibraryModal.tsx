/**
 * LibraryModal Component
 *
 * Modal for managing saved SQL queries - view, create, edit, delete, upload, download
 */

import { useState, useRef, useEffect } from 'react'
import { X, Search, Plus, Upload, FolderDown } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import JSZip from 'jszip'
import * as settingsApi from '@/lib/settingsApi'

// Components
import { QueryRow } from './QueryRow'
import { NewQueryEditor } from './NewQueryEditor'
import { EditQueryEditor } from './EditQueryEditor'
import { DeleteConfirmDialog } from './DeleteConfirmDialog'

export interface LibraryModalProps {
  isOpen: boolean
  onClose: () => void
  onLoadQuery?: (query: settingsApi.SavedQuery) => void
  initialCodeData?: { name: string; content: string } | null
}

export function LibraryModal({ isOpen, onClose, onLoadQuery, initialCodeData }: LibraryModalProps) {
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  // State
  const [searchQuery, setSearchQuery] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [renamingId, setRenamingId] = useState<number | null>(null)
  const [newName, setNewName] = useState('')
  const [showNewEditor, setShowNewEditor] = useState(false)
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null)
  const [uploadedQuery, setUploadedQuery] = useState<{ name: string; content: string } | null>(null)

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

  // Open editor with code from CodeEditor download button
  useEffect(() => {
    if (initialCodeData && isOpen) {
      setUploadedQuery(initialCodeData)
      setShowNewEditor(true)
    }
  }, [initialCodeData, isOpen])

  // Data fetching
  const { data: queries, isLoading } = useQuery({
    queryKey: ['saved-queries'],
    queryFn: () => settingsApi.getSavedQueries(),
  })

  // Mutations
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
      await Promise.all(files.map((f) => settingsApi.saveQuery(f)))
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-queries'] })
    },
  })

  // Handlers
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files || files.length === 0) return

    const file = files[0]
    const ext = file.name.split('.').pop()?.toLowerCase()

    if (ext !== 'sql') {
      alert('Only .sql files are supported')
      event.target.value = ''
      return
    }

    const content = await file.text()
    const name = file.name.replace(/\.sql$/, '')

    setUploadedQuery({ name, content })
    setShowNewEditor(true)
    event.target.value = ''
  }

  const handleBulkExport = async () => {
    if (!queries || queries.length === 0) {
      alert('No queries to export')
      return
    }

    try {
      const zip = new JSZip()
      queries.forEach((query) => {
        zip.file(`${query.name}.sql`, query.query)
      })

      const blob = await zip.generateAsync({ type: 'blob' })
      const now = new Date()
      const timestamp = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`

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

  const handleDownloadQuery = (query: settingsApi.SavedQuery) => {
    const blob = new Blob([query.query], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${query.name}.sql`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  // Filter queries
  const filteredQueries =
    queries?.filter(
      (q) =>
        q.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        q.query.toLowerCase().includes(searchQuery.toLowerCase())
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
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Library</h2>
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
              <span className="text-green-900 dark:text-green-100">
                ✓ Files uploaded successfully!
              </span>
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
              onSave={() => setEditingId(null)}
            />
          )}

          {/* Query List */}
          {!showNewEditor && !editingId && (
            <div className="space-y-2">
              {isLoading ? (
                <div className="text-center py-8 text-gray-500">Loading...</div>
              ) : filteredQueries.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  {searchQuery
                    ? 'No queries found'
                    : 'No saved queries yet. Click "+ New" to create one.'}
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
                    onDownload={() => handleDownloadQuery(query)}
                  />
                ))
              )}
            </div>
          )}
        </div>

        {/* Delete Confirmation Dialog */}
        {deleteConfirmId && (
          <DeleteConfirmDialog
            queryName={queries?.find((q) => q.id === deleteConfirmId)?.name || ''}
            onConfirm={() => deleteMutation.mutate(deleteConfirmId)}
            onCancel={() => setDeleteConfirmId(null)}
          />
        )}
      </div>
    </div>
  )
}
