import { useState, useEffect } from 'react'
import { Save, Zap, Database, Users } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as settingsApi from '@/lib/settingsApi'

export default function AdvancedTab() {
  const queryClient = useQueryClient()
  const [localSettings, setLocalSettings] = useState<settingsApi.AppSettings | null>(null)

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

  return (
    <div className="space-y-8">
      {/* Database Performance */}
      <div>
        <div className="flex items-center space-x-2 mb-4">
          <Database className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Database Performance
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Configure database caching and query optimization
            </p>
          </div>
        </div>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Database cache size: {localSettings.database_cache_size_mb} MB
            </label>
            <input
              type="range"
              min="64"
              max="2048"
              step="64"
              value={localSettings.database_cache_size_mb}
              onChange={(e) =>
                setLocalSettings({
                  ...localSettings,
                  database_cache_size_mb: parseInt(e.target.value),
                })
              }
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Memory allocated for database caching (64MB - 2GB)
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Max query timeout: {localSettings.max_query_timeout_seconds}s
            </label>
            <input
              type="range"
              min="30"
              max="600"
              step="30"
              value={localSettings.max_query_timeout_seconds}
              onChange={(e) =>
                setLocalSettings({
                  ...localSettings,
                  max_query_timeout_seconds: parseInt(e.target.value),
                })
              }
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Maximum time allowed for a single query (30s - 10min)
            </p>
          </div>

          <div>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={localSettings.enable_query_optimization}
                onChange={(e) =>
                  setLocalSettings({ ...localSettings, enable_query_optimization: e.target.checked })
                }
                className="rounded"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Enable query optimization
              </span>
            </label>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 ml-6">
              Automatically optimize queries for better performance
            </p>
          </div>
        </div>
      </div>

      {/* Automation & Workflows */}
      <div>
        <div className="flex items-center space-x-2 mb-4">
          <Zap className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Automation & Workflows
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Configure automated tasks and workflow execution
            </p>
          </div>
        </div>
        <div className="space-y-4">
          <div>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={localSettings.automation_enabled}
                onChange={(e) =>
                  setLocalSettings({ ...localSettings, automation_enabled: e.target.checked })
                }
                className="rounded"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Enable automation
              </span>
            </label>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 ml-6">
              Allow automated tasks and workflows to run
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Auto-save interval: {localSettings.auto_save_interval_seconds}s
            </label>
            <input
              type="range"
              min="30"
              max="600"
              step="30"
              value={localSettings.auto_save_interval_seconds}
              onChange={(e) =>
                setLocalSettings({
                  ...localSettings,
                  auto_save_interval_seconds: parseInt(e.target.value),
                })
              }
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              How often to automatically save work (30s - 10min)
            </p>
          </div>

          <div>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={localSettings.auto_backup_enabled}
                onChange={(e) =>
                  setLocalSettings({ ...localSettings, auto_backup_enabled: e.target.checked })
                }
                className="rounded"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Enable automatic backups
              </span>
            </label>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 ml-6">
              Automatically backup queries and data
            </p>
          </div>

          <div>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={localSettings.workflow_execution_enabled}
                onChange={(e) =>
                  setLocalSettings({ ...localSettings, workflow_execution_enabled: e.target.checked })
                }
                className="rounded"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Enable workflow execution
              </span>
            </label>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 ml-6">
              Allow custom workflows to execute automatically
            </p>
          </div>
        </div>
      </div>

      {/* Power User Features */}
      <div>
        <div className="flex items-center space-x-2 mb-4">
          <Users className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Power User Features
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Advanced capabilities for experienced users
            </p>
          </div>
        </div>
        <div className="space-y-4">
          <div>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={localSettings.enable_semantic_search}
                onChange={(e) =>
                  setLocalSettings({ ...localSettings, enable_semantic_search: e.target.checked })
                }
                className="rounded"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Enable semantic search
              </span>
            </label>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 ml-6">
              Use AI-powered semantic search for queries
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Semantic similarity threshold: {localSettings.semantic_similarity_threshold.toFixed(2)}
            </label>
            <input
              type="range"
              min="0.1"
              max="1.0"
              step="0.05"
              value={localSettings.semantic_similarity_threshold}
              onChange={(e) =>
                setLocalSettings({
                  ...localSettings,
                  semantic_similarity_threshold: parseFloat(e.target.value),
                })
              }
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
              disabled={!localSettings.enable_semantic_search}
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Minimum similarity score for search results (0.1 - 1.0)
            </p>
          </div>

          <div>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={localSettings.show_keyboard_shortcuts}
                onChange={(e) =>
                  setLocalSettings({ ...localSettings, show_keyboard_shortcuts: e.target.checked })
                }
                className="rounded"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Show keyboard shortcuts
              </span>
            </label>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 ml-6">
              Display keyboard shortcuts in the UI
            </p>
          </div>

          <div>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={localSettings.enable_bulk_operations}
                onChange={(e) =>
                  setLocalSettings({ ...localSettings, enable_bulk_operations: e.target.checked })
                }
                className="rounded"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Enable bulk operations
              </span>
            </label>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 ml-6">
              Allow batch processing of multiple files or queries
            </p>
          </div>
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
