import { useState, useEffect } from 'react'
import { Save } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as settingsApi from '@/lib/settingsApi'

export default function PowerUserTab() {
  const queryClient = useQueryClient()
  const [localSettings, setLocalSettings] = useState<settingsApi.AppSettings | null>(null)
  const [importFile, setImportFile] = useState<File | null>(null)

  const { data: settings, isLoading } = useQuery({
    queryKey: ['app-settings'],
    queryFn: settingsApi.getSettings,
  })

  const saveMutation = useMutation({
    mutationFn: settingsApi.updateSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['app-settings'] })
    },
  })

  useEffect(() => {
    if (settings) {
      setLocalSettings(settings)
    }
  }, [settings])

  if (isLoading || !localSettings) {
    return <div className="text-center py-8 text-gray-500">Loading...</div>
  }

  const handleSave = () => {
    if (localSettings) {
      saveMutation.mutate(localSettings)
    }
  }

  const handleExportLibrary = async () => {
    try {
      const queries = await settingsApi.getSavedQueries({})
      const blob = new Blob([JSON.stringify(queries, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `neutron_library_export_${Date.now()}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Export failed:', error)
      alert('Failed to export library')
    }
  }

  const handleImportLibrary = async () => {
    if (!importFile) return
    try {
      const text = await importFile.text()
      const queries = JSON.parse(text)
      for (const query of queries) {
        await settingsApi.saveQuery(query)
      }
      alert(`Imported ${queries.length} queries successfully`)
      setImportFile(null)
    } catch (error) {
      console.error('Import failed:', error)
      alert('Failed to import library')
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          Semantic Search
        </h3>
        <div className="space-y-4">
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={localSettings.enable_semantic_search}
              onChange={(e) =>
                setLocalSettings({
                  ...localSettings,
                  enable_semantic_search: e.target.checked
                })
              }
              className="rounded"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">
              Enable hybrid semantic search
            </span>
          </label>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Similarity threshold: {localSettings.semantic_similarity_threshold.toFixed(1)}
            </label>
            <input
              type="range"
              min="0.1"
              max="1.0"
              step="0.1"
              value={localSettings.semantic_similarity_threshold}
              onChange={(e) =>
                setLocalSettings({
                  ...localSettings,
                  semantic_similarity_threshold: parseFloat(e.target.value)
                })
              }
              className="w-full"
            />
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          Library Management
        </h3>
        <div className="space-y-3">
          <button
            onClick={handleExportLibrary}
            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            Export Library to JSON
          </button>
          <div className="space-y-2">
            <input
              type="file"
              accept=".json"
              onChange={(e) => setImportFile(e.target.files?.[0] || null)}
              className="w-full text-sm text-gray-700 dark:text-gray-300"
            />
            <button
              onClick={handleImportLibrary}
              disabled={!importFile}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Import Library from JSON
            </button>
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          Advanced Features
        </h3>
        <div className="space-y-3">
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={localSettings.show_keyboard_shortcuts}
              onChange={(e) =>
                setLocalSettings({
                  ...localSettings,
                  show_keyboard_shortcuts: e.target.checked
                })
              }
              className="rounded"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">
              Show keyboard shortcuts overlay
            </span>
          </label>
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={localSettings.enable_bulk_operations}
              onChange={(e) =>
                setLocalSettings({
                  ...localSettings,
                  enable_bulk_operations: e.target.checked
                })
              }
              className="rounded"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">
              Enable bulk operations
            </span>
          </label>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end pt-4 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={handleSave}
          disabled={saveMutation.isPending}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-2"
        >
          <Save className="w-4 h-4" />
          <span>{saveMutation.isPending ? 'Saving...' : 'Save Settings'}</span>
        </button>
      </div>

      {saveMutation.isSuccess && (
        <div className="text-green-600 text-sm text-center">Settings saved successfully!</div>
      )}
    </div>
  )
}
