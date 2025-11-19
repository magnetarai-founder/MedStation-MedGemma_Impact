/**
 * NewDocumentEditor Component
 *
 * Form for creating a new project document with Monaco editor
 */

import { useState } from 'react'
import { X } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import Editor from '@monaco-editor/react'
import { api } from '@/lib/api'
import { TagInput } from './TagInput'

interface NewDocumentEditorProps {
  initialData?: { name: string; content: string } | null
  onClose: () => void
  onSave: () => void
}

export function NewDocumentEditor({ initialData, onClose, onSave }: NewDocumentEditorProps) {
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
