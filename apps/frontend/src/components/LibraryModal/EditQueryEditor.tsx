/**
 * EditQueryEditor Component
 *
 * Form for editing an existing saved query with Monaco editor
 */

import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Editor from '@monaco-editor/react'
import * as settingsApi from '@/lib/settingsApi'

interface EditQueryEditorProps {
  queryId: number
  onClose: () => void
  onSave: () => void
}

export function EditQueryEditor({ queryId, onClose, onSave }: EditQueryEditorProps) {
  const queryClient = useQueryClient()
  const { data: queries } = useQuery({
    queryKey: ['saved-queries'],
    queryFn: () => settingsApi.getSavedQueries(),
  })

  const query = queries?.find((q) => q.id === queryId)
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
    mutationFn: () =>
      settingsApi.updateQuery(queryId, {
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
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Edit Query</h3>
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
