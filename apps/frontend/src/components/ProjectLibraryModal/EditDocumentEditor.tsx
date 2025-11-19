/**
 * EditDocumentEditor Component
 *
 * Form for editing an existing project document with Monaco editor
 */

import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Editor from '@monaco-editor/react'
import { api } from '@/lib/api'
import { TagInput } from './TagInput'
import type { ProjectDocument } from './types'

interface EditDocumentEditorProps {
  documentId: number
  onClose: () => void
  onSave: () => void
}

export function EditDocumentEditor({ documentId, onClose, onSave }: EditDocumentEditorProps) {
  const queryClient = useQueryClient()
  const { data: documents } = useQuery({
    queryKey: ['project-documents'],
    queryFn: async () => {
      const res = await api.get('/code/library')
      return res.data as ProjectDocument[]
    },
  })

  const document = documents?.find((d) => d.id === documentId)
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
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Edit Document</h3>
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
