/**
 * NewQueryEditor Component
 *
 * Form for creating a new saved query with Monaco editor
 */

import { useState } from 'react'
import { X } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import Editor from '@monaco-editor/react'
import * as settingsApi from '@/lib/settingsApi'

interface NewQueryEditorProps {
  initialData?: { name: string; content: string } | null
  onClose: () => void
  onSave: () => void
}

export function NewQueryEditor({ initialData, onClose, onSave }: NewQueryEditorProps) {
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
