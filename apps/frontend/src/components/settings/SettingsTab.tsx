import { useState, useEffect } from 'react'
import { Save, Settings, Zap, Database, FileJson, Users, Clock, Cpu } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as settingsApi from '@/lib/settingsApi'
import { type NavTab } from '@/stores/navigationStore'
import ChatSettingsContent from './ChatSettingsContent'
import FormatNamingRow from './FormatNamingRow'

interface SettingsTabProps {
  activeNavTab: NavTab
}

export default function SettingsTab({ activeNavTab }: SettingsTabProps) {
  const queryClient = useQueryClient()
  const [localSettings, setLocalSettings] = useState<settingsApi.AppSettings | null>(null)
  const [customizePerFormat, setCustomizePerFormat] = useState(false)
  const [previewName, setPreviewName] = useState('')

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
      // Check if any per-format patterns are set
      const hasCustomFormats = !!(
        settings.naming_pattern_sql_excel ||
        settings.naming_pattern_sql_csv ||
        settings.naming_pattern_json_excel
      )
      setCustomizePerFormat(hasCustomFormats)
    }
  }, [settings])

  // Update preview when pattern changes
  useEffect(() => {
    if (localSettings) {
      const preview = generatePreview(localSettings.naming_pattern_global)
      setPreviewName(preview)
    }
  }, [localSettings?.naming_pattern_global])

  const generatePreview = (pattern: string) => {
    const now = new Date()
    const yyyy = now.getFullYear().toString()
    const mm = (now.getMonth() + 1).toString().padStart(2, '0')
    const dd = now.getDate().toString().padStart(2, '0')
    const hh = now.getHours().toString().padStart(2, '0')
    const min = now.getMinutes().toString().padStart(2, '0')
    const ss = now.getSeconds().toString().padStart(2, '0')

    return pattern
      .replace('{name}', 'customer_analytics')
      .replace('{type}', 'sql')
      .replace('{format}', 'excel')
      .replace('{YYYYMMDD}', `${yyyy}${mm}${dd}`)
      .replace('{YYYY}', yyyy)
      .replace('{MM}', mm)
      .replace('{DD}', dd)
      .replace('{HH}', hh)
      .replace('{mm}', min)
      .replace('{ss}', ss)
      .replace('{timestamp}', Math.floor(now.getTime() / 1000).toString())
  }

  const validatePattern = (pattern: string) => {
    const validVars = ['{name}', '{type}', '{format}', '{YYYY}', '{MM}', '{DD}', '{YYYYMMDD}', '{HH}', '{mm}', '{ss}', '{timestamp}']
    const matches = pattern.match(/\{[^}]+\}/g) || []
    const invalid = matches.filter(m => !validVars.includes(m))
    return invalid.length > 0 ? `Unknown variable: ${invalid.join(', ')}` : null
  }

  const validationError = localSettings ? validatePattern(localSettings.naming_pattern_global) : null

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
      {/* AI Chat Settings */}
      <ChatSettingsContent />

      {/* Divider */}
      <div className="border-t border-gray-200 dark:border-gray-700"></div>

      {/* App Settings */}
      <>
          {/* Performance & Memory */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Performance & Memory
            </h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Max Upload File Size: {localSettings.max_file_size_mb} MB
            </label>
            <input
              type="range"
              min="100"
              max="2000"
              value={localSettings.max_file_size_mb}
              onChange={(e) =>
                setLocalSettings({
                  ...localSettings,
                  max_file_size_mb: parseInt(e.target.value),
                })
              }
              className="w-full"
            />
          </div>

          <div>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={localSettings.enable_chunked_processing}
                onChange={(e) =>
                  setLocalSettings({
                    ...localSettings,
                    enable_chunked_processing: e.target.checked,
                  })
                }
                className="rounded"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Enable chunked processing
              </span>
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Chunk Size (rows)
            </label>
            <input
              type="number"
              value={localSettings.chunk_size_rows}
              onChange={(e) =>
                setLocalSettings({
                  ...localSettings,
                  chunk_size_rows: parseInt(e.target.value),
                })
              }
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            />
          </div>
        </div>
      </div>

      {/* Default Download Options */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          Default Download Options
        </h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              SQL Query Results Format
            </label>
            <select
              value={localSettings.sql_default_format}
              onChange={(e) =>
                setLocalSettings({ ...localSettings, sql_default_format: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            >
              <option value="excel">Excel</option>
              <option value="csv">CSV</option>
              <option value="tsv">TSV</option>
              <option value="parquet">Parquet</option>
              <option value="json">JSON</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              JSON Conversion Format
            </label>
            <select
              value={localSettings.json_default_format}
              onChange={(e) =>
                setLocalSettings({ ...localSettings, json_default_format: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            >
              <option value="excel">Excel</option>
              <option value="csv">CSV</option>
              <option value="tsv">TSV</option>
              <option value="parquet">Parquet</option>
            </select>
          </div>

          <div>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={localSettings.json_auto_safe}
                onChange={(e) =>
                  setLocalSettings({ ...localSettings, json_auto_safe: e.target.checked })
                }
                className="rounded"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                JSON Auto-safe mode
              </span>
            </label>
          </div>
        </div>
      </div>

      {/* JSON Processing Settings */}
      <div>
        <div className="flex items-center space-x-2 mb-4">
          <FileJson className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            JSON Processing
          </h3>
        </div>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Max JSON Depth: {localSettings.json_max_depth}
            </label>
            <input
              type="range"
              min="1"
              max="20"
              value={localSettings.json_max_depth}
              onChange={(e) =>
                setLocalSettings({
                  ...localSettings,
                  json_max_depth: parseInt(e.target.value),
                })
              }
              className="w-full"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Maximum depth for nested JSON structures
            </p>
          </div>

          <div>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={localSettings.json_flatten_arrays}
                onChange={(e) =>
                  setLocalSettings({ ...localSettings, json_flatten_arrays: e.target.checked })
                }
                className="rounded"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Flatten nested arrays
              </span>
            </label>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 ml-6">
              Convert nested arrays to separate columns when possible
            </p>
          </div>

          <div>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={localSettings.json_preserve_nulls}
                onChange={(e) =>
                  setLocalSettings({ ...localSettings, json_preserve_nulls: e.target.checked })
                }
                className="rounded"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Preserve null values
              </span>
            </label>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 ml-6">
              Keep null values in output instead of removing them
            </p>
          </div>
        </div>
      </div>

      {/* Automation & Workflows */}
      <div>
        <div className="flex items-center space-x-2 mb-4">
          <Zap className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Automation & Workflows
          </h3>
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
              className="w-full"
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

      {/* Database Performance */}
      <div>
        <div className="flex items-center space-x-2 mb-4">
          <Database className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Database Performance
          </h3>
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
              className="w-full"
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
              className="w-full"
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

      {/* Memory Allocation */}
      <div>
        <div className="flex items-center space-x-2 mb-4">
          <Cpu className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Memory Allocation
          </h3>
        </div>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              App memory: {localSettings.app_memory_percent}%
            </label>
            <input
              type="range"
              min="10"
              max="80"
              value={localSettings.app_memory_percent}
              onChange={(e) =>
                setLocalSettings({
                  ...localSettings,
                  app_memory_percent: parseInt(e.target.value),
                })
              }
              className="w-full"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Percentage of system memory for app operations
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Processing memory: {localSettings.processing_memory_percent}%
            </label>
            <input
              type="range"
              min="10"
              max="80"
              value={localSettings.processing_memory_percent}
              onChange={(e) =>
                setLocalSettings({
                  ...localSettings,
                  processing_memory_percent: parseInt(e.target.value),
                })
              }
              className="w-full"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Percentage of system memory for data processing
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Cache memory: {localSettings.cache_memory_percent}%
            </label>
            <input
              type="range"
              min="5"
              max="40"
              value={localSettings.cache_memory_percent}
              onChange={(e) =>
                setLocalSettings({
                  ...localSettings,
                  cache_memory_percent: parseInt(e.target.value),
                })
              }
              className="w-full"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Percentage of system memory for caching
            </p>
          </div>
        </div>
      </div>

      {/* Power User Features */}
      <div>
        <div className="flex items-center space-x-2 mb-4">
          <Users className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Power User Features
          </h3>
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
              className="w-full"
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

      {/* Session Settings */}
      <div>
        <div className="flex items-center space-x-2 mb-4">
          <Clock className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Session Settings
          </h3>
        </div>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Session timeout: {localSettings.session_timeout_hours} hours
            </label>
            <input
              type="range"
              min="1"
              max="168"
              value={localSettings.session_timeout_hours}
              onChange={(e) =>
                setLocalSettings({
                  ...localSettings,
                  session_timeout_hours: parseInt(e.target.value),
                })
              }
              className="w-full"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Automatically log out after inactivity (1 hour - 7 days)
            </p>
          </div>

          <div>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={localSettings.clear_temp_on_close}
                onChange={(e) =>
                  setLocalSettings({ ...localSettings, clear_temp_on_close: e.target.checked })
                }
                className="rounded"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Clear temporary files on close
              </span>
            </label>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 ml-6">
              Automatically delete temporary files when session ends
            </p>
          </div>
        </div>
      </div>

      {/* Download Naming Convention */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          Download Naming Convention
        </h3>
        <div className="space-y-4">
          {/* Preset Templates */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Apply Template
            </label>
            <select
              onChange={(e) => {
                if (e.target.value) {
                  setLocalSettings({
                    ...localSettings,
                    naming_pattern_global: e.target.value
                  })
                }
              }}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            >
              <option value="">-- Select Template --</option>
              <option value="{name}_{YYYYMMDD}">Descriptive: {generatePreview('{name}_{YYYYMMDD}')}</option>
              <option value="{name}_{timestamp}">Timestamped: {generatePreview('{name}_{timestamp}')}</option>
              <option value="{type}_{name}_{YYYY}-{MM}-{DD}">Professional: {generatePreview('{type}_{name}_{YYYY}-{MM}-{DD}')}</option>
            </select>
          </div>

          {/* Global Pattern */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Global Default Pattern
            </label>
            <input
              type="text"
              value={localSettings.naming_pattern_global}
              onChange={(e) =>
                setLocalSettings({
                  ...localSettings,
                  naming_pattern_global: e.target.value
                })
              }
              placeholder="{name}_{YYYYMMDD}"
              className={`w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 ${
                validationError
                  ? 'border-red-500'
                  : 'border-gray-300 dark:border-gray-600'
              }`}
            />
            {validationError && (
              <p className="text-red-500 text-sm mt-1">{validationError}</p>
            )}
            <div className="text-sm text-gray-500 dark:text-gray-400 mt-2">
              <div className="font-medium mb-1">Preview: {previewName}.xlsx</div>
              <div className="space-y-1">
                <div>Available variables:</div>
                <div className="grid grid-cols-2 gap-x-4">
                  <span>• {'{name}'} - Query/file name</span>
                  <span>• {'{type}'} - sql/json</span>
                  <span>• {'{format}'} - excel/csv/parquet</span>
                  <span>• {'{YYYYMMDD}'} - Date shorthand (20251007)</span>
                  <span>• {'{YYYY}'}, {'{MM}'}, {'{DD}'} - Date parts</span>
                  <span>• {'{HH}'}, {'{mm}'}, {'{ss}'} - Time</span>
                  <span>• {'{timestamp}'} - Unix timestamp</span>
                </div>
              </div>
            </div>
          </div>

          {/* Customize Per Format */}
          <div>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={customizePerFormat}
                onChange={(e) => setCustomizePerFormat(e.target.checked)}
                className="rounded"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Customize per format
              </span>
            </label>
          </div>

          {customizePerFormat && (
            <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg space-y-4">
              <div>
                <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-3">
                  SQL Query Exports
                </h4>
                <FormatNamingRow
                  format="Excel"
                  defaultPattern={localSettings.naming_pattern_global}
                  value={localSettings.naming_pattern_sql_excel}
                  onChange={(val) => setLocalSettings({ ...localSettings, naming_pattern_sql_excel: val })}
                />
                <FormatNamingRow
                  format="CSV"
                  defaultPattern={localSettings.naming_pattern_global}
                  value={localSettings.naming_pattern_sql_csv}
                  onChange={(val) => setLocalSettings({ ...localSettings, naming_pattern_sql_csv: val })}
                />
                <FormatNamingRow
                  format="TSV"
                  defaultPattern={localSettings.naming_pattern_global}
                  value={localSettings.naming_pattern_sql_tsv}
                  onChange={(val) => setLocalSettings({ ...localSettings, naming_pattern_sql_tsv: val })}
                />
                <FormatNamingRow
                  format="Parquet"
                  defaultPattern={localSettings.naming_pattern_global}
                  value={localSettings.naming_pattern_sql_parquet}
                  onChange={(val) => setLocalSettings({ ...localSettings, naming_pattern_sql_parquet: val })}
                />
                <FormatNamingRow
                  format="JSON"
                  defaultPattern={localSettings.naming_pattern_global}
                  value={localSettings.naming_pattern_sql_json}
                  onChange={(val) => setLocalSettings({ ...localSettings, naming_pattern_sql_json: val })}
                />
              </div>

              <div>
                <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-3">
                  JSON Conversion Exports
                </h4>
                <FormatNamingRow
                  format="Excel"
                  defaultPattern={localSettings.naming_pattern_global}
                  value={localSettings.naming_pattern_json_excel}
                  onChange={(val) => setLocalSettings({ ...localSettings, naming_pattern_json_excel: val })}
                />
                <FormatNamingRow
                  format="CSV"
                  defaultPattern={localSettings.naming_pattern_global}
                  value={localSettings.naming_pattern_json_csv}
                  onChange={(val) => setLocalSettings({ ...localSettings, naming_pattern_json_csv: val })}
                />
                <FormatNamingRow
                  format="TSV"
                  defaultPattern={localSettings.naming_pattern_global}
                  value={localSettings.naming_pattern_json_tsv}
                  onChange={(val) => setLocalSettings({ ...localSettings, naming_pattern_json_tsv: val })}
                />
                <FormatNamingRow
                  format="Parquet"
                  defaultPattern={localSettings.naming_pattern_global}
                  value={localSettings.naming_pattern_json_parquet}
                  onChange={(val) => setLocalSettings({ ...localSettings, naming_pattern_json_parquet: val })}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end pt-4 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={handleSave}
          disabled={saveMutation.isPending || !!validationError}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-2"
        >
          <Save className="w-4 h-4" />
          <span>{saveMutation.isPending ? 'Saving...' : 'Save Settings'}</span>
        </button>
      </div>

      {saveMutation.isSuccess && (
        <div className="text-green-600 text-sm text-center">Settings saved successfully!</div>
      )}
      </>
    </div>
  )
}
