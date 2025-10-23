import { useState, useEffect } from 'react'
import { X, Settings as SettingsIcon, Zap, AlertTriangle, Save, Download, Star, Loader2, CheckCircle2, Circle, Cpu, User } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as settingsApi from '@/lib/settingsApi'
import { type NavTab } from '@/stores/navigationStore'
import { useChatStore } from '@/stores/chatStore'
import { ProfileSettings } from './ProfileSettings'


interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
  activeNavTab: NavTab
}


export function SettingsModal({ isOpen, onClose, activeNavTab }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<'profile' | 'settings' | 'power' | 'models' | 'danger'>('settings')

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

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
      />

      {/* Modal */}
      <div className="relative w-full max-w-4xl max-h-[85vh] bg-white dark:bg-gray-900 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <SettingsIcon className="w-6 h-6 text-primary-600 dark:text-primary-400" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              Global Settings
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 dark:border-gray-700 px-6">
          <button
            onClick={() => setActiveTab('profile')}
            className={`
              flex items-center space-x-2 px-4 py-3 border-b-2 transition-colors
              ${activeTab === 'profile'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }
            `}
          >
            <User className="w-4 h-4" />
            <span className="font-medium">Profile</span>
          </button>
          <button
            onClick={() => setActiveTab('settings')}
            className={`
              flex items-center space-x-2 px-4 py-3 border-b-2 transition-colors
              ${activeTab === 'settings'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }
            `}
          >
            <SettingsIcon className="w-4 h-4" />
            <span className="font-medium">App Settings</span>
          </button>
          <button
            onClick={() => setActiveTab('power')}
            className={`
              flex items-center space-x-2 px-4 py-3 border-b-2 transition-colors
              ${activeTab === 'power'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }
            `}
          >
            <Zap className="w-4 h-4" />
            <span className="font-medium">Advanced</span>
          </button>
          <button
            onClick={() => setActiveTab('models')}
            className={`
              flex items-center space-x-2 px-4 py-3 border-b-2 transition-colors
              ${activeTab === 'models'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }
            `}
          >
            <Cpu className="w-4 h-4" />
            <span className="font-medium">Model Management</span>
          </button>
          <button
            onClick={() => setActiveTab('danger')}
            className={`
              flex items-center space-x-2 px-4 py-3 border-b-2 transition-colors
              ${activeTab === 'danger'
                ? 'border-red-500 text-red-600 dark:text-red-400'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }
            `}
          >
            <AlertTriangle className="w-4 h-4" />
            <span className="font-medium">Danger Zone</span>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {activeTab === 'profile' && <ProfileSettings />}
          {activeTab === 'settings' && <SettingsTab activeNavTab={activeNavTab} />}
          {activeTab === 'power' && <PowerUserTab />}
          {activeTab === 'models' && <ModelManagementTab />}
          {activeTab === 'danger' && <DangerZoneTab />}
        </div>
      </div>
    </div>
  )
}

function SettingsTab({ activeNavTab }: { activeNavTab: NavTab }) {
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

function FormatNamingRow({
  format,
  defaultPattern,
  value,
  onChange
}: {
  format: string
  defaultPattern: string
  value: string | null | undefined
  onChange: (val: string | null) => void
}) {
  const mode = value ? 'custom' : 'default'

  return (
    <div className="flex items-center space-x-3 mb-2">
      <label className="w-20 text-sm text-gray-700 dark:text-gray-300">{format}:</label>
      <select
        value={mode}
        onChange={(e) => {
          if (e.target.value === 'default') {
            onChange(null)
          } else {
            onChange(defaultPattern)
          }
        }}
        className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 text-sm"
      >
        <option value="default">Default</option>
        <option value="custom">Custom</option>
      </select>
      {mode === 'custom' && (
        <input
          type="text"
          value={value || defaultPattern}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Custom pattern"
          className="flex-1 px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 text-sm"
        />
      )}
    </div>
  )
}

function PowerUserTab() {
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

function ChatSettingsContent() {
  const {
    settings,
    availableModels,
    setAvailableModels,
    updateSettings
  } = useChatStore()

  // Ensure settings have all required fields with defaults
  const safeSettings = {
    tone: settings.tone || 'balanced',
    temperature: settings.temperature ?? 0.7,
    topP: settings.topP ?? 0.9,
    topK: settings.topK ?? 40,
    repeatPenalty: settings.repeatPenalty ?? 1.1,
    systemPrompt: settings.systemPrompt || '',
    ...settings
  }

  // Load models on mount
  useEffect(() => {
    const loadModels = async () => {
      try {
        const response = await fetch(`/api/v1/chat/models`)
        if (response.ok) {
          const models = await response.json()
          setAvailableModels(models)
        }
      } catch (error) {
        console.error('Failed to load models:', error)
      }
    }
    loadModels()
  }, [setAvailableModels])

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          AI Chat Parameters
        </h3>

        <div className="space-y-4">
          {/* Model Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Default Model
            </label>
            <select
              value={settings.defaultModel}
              onChange={(e) => updateSettings({ defaultModel: e.target.value })}
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            >
              {availableModels.length === 0 ? (
                <option value="">Loading models...</option>
              ) : (
                availableModels.map((model) => (
                  <option key={model.name} value={model.name}>
                    {model.name} ({model.size})
                  </option>
                ))
              )}
            </select>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Pre-loaded on app start</p>
          </div>

          {/* Tone Presets */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Tone Preset
            </label>
            <div className="grid grid-cols-2 gap-2">
              {(['creative', 'balanced', 'precise', 'custom'] as const).map((tone) => (
                <button
                  key={tone}
                  onClick={() => updateSettings({ tone })}
                  className={`px-3 py-2 text-xs font-medium rounded-lg border transition-all ${
                    safeSettings.tone === tone
                      ? 'bg-primary-100 dark:bg-primary-900/30 border-primary-500 text-primary-700 dark:text-primary-300'
                      : 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:border-primary-300'
                  }`}
                >
                  {tone.charAt(0).toUpperCase() + tone.slice(1)}
                </button>
              ))}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {safeSettings.tone === 'creative' && 'Higher temp, more creative & varied'}
              {safeSettings.tone === 'balanced' && 'Balanced creativity & accuracy'}
              {safeSettings.tone === 'precise' && 'Lower temp, more focused & deterministic'}
              {safeSettings.tone === 'custom' && 'Use custom parameters below'}
            </p>
          </div>

          {/* Temperature */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Temperature
              </label>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {safeSettings.temperature.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="2"
              step="0.05"
              value={safeSettings.temperature}
              onChange={(e) => updateSettings({ temperature: parseFloat(e.target.value), tone: 'custom' })}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
              disabled={safeSettings.tone !== 'custom'}
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Controls randomness (0 = deterministic, 2 = very creative)</p>
          </div>

          {/* Top P */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Top P (Nucleus Sampling)
              </label>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {safeSettings.topP.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={safeSettings.topP}
              onChange={(e) => updateSettings({ topP: parseFloat(e.target.value), tone: 'custom' })}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
              disabled={safeSettings.tone !== 'custom'}
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Cumulative probability cutoff for token selection</p>
          </div>

          {/* Top K */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Top K
              </label>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {safeSettings.topK}
              </span>
            </div>
            <input
              type="range"
              min="1"
              max="100"
              step="1"
              value={safeSettings.topK}
              onChange={(e) => updateSettings({ topK: parseInt(e.target.value), tone: 'custom' })}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
              disabled={safeSettings.tone !== 'custom'}
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Limits sampling to top K most likely tokens</p>
          </div>

          {/* Repeat Penalty */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Repeat Penalty
              </label>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {safeSettings.repeatPenalty.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="2"
              step="0.05"
              value={safeSettings.repeatPenalty}
              onChange={(e) => updateSettings({ repeatPenalty: parseFloat(e.target.value), tone: 'custom' })}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
              disabled={safeSettings.tone !== 'custom'}
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Penalizes repetition (1.0 = no penalty, higher = less repetition)</p>
          </div>

          {/* System Prompt */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              System Prompt
            </label>
            <textarea
              value={safeSettings.systemPrompt}
              onChange={(e) => updateSettings({ systemPrompt: e.target.value })}
              placeholder="You are a helpful AI assistant..."
              rows={3}
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 resize-none"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Instructions sent with every message</p>
          </div>

          {/* Auto-generate titles */}
          <div className="flex items-center justify-between">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Auto-generate titles</label>
              <p className="text-xs text-gray-500 dark:text-gray-400">Name chats from first message</p>
            </div>
            <input
              type="checkbox"
              checked={settings.autoGenerateTitles}
              onChange={(e) => updateSettings({ autoGenerateTitles: e.target.checked })}
              className="w-4 h-4 rounded text-primary-600"
            />
          </div>

          {/* Context Window (locked) */}
          <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
            <p className="text-sm font-medium text-gray-900 dark:text-gray-100">Context Window: 200k tokens</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Full conversation history sent to model for optimal context preservation</p>
          </div>
        </div>
      </div>

      {/* Model Manager Section */}
      <ModelManagerSection />
    </div>
  )
}

function ModelManagerSection() {
  const [favorites, setFavorites] = useState<string[]>([])

  // Query for model status
  const { data: modelStatus, isLoading, refetch } = useQuery({
    queryKey: ['model-status'],
    queryFn: async () => {
      const response = await fetch('/api/v1/chat/models/status')
      if (!response.ok) throw new Error('Failed to load model status')
      return await response.json()
    },
    refetchInterval: 5000 // Refresh every 5 seconds
  })

  // Load favorites
  useEffect(() => {
    const loadFavorites = async () => {
      try {
        const response = await fetch('/api/v1/chat/models/favorites')
        if (response.ok) {
          const data = await response.json()
          setFavorites(data.favorites || [])
        }
      } catch (error) {
        console.error('Failed to load favorites:', error)
      }
    }
    loadFavorites()
  }, [])

  const toggleFavorite = async (modelName: string) => {
    const isFavorite = favorites.includes(modelName)
    try {
      const method = isFavorite ? 'DELETE' : 'POST'
      const response = await fetch(`/api/v1/chat/models/favorites/${encodeURIComponent(modelName)}`, { method })

      if (response.ok) {
        const data = await response.json()
        setFavorites(data.favorites || [])
      }
    } catch (error) {
      console.error('Failed to toggle favorite:', error)
    }
  }

  const preloadModel = async (modelName: string) => {
    try {
      await fetch(`/api/v1/chat/models/preload?model=${encodeURIComponent(modelName)}&keep_alive=1h`, { method: 'POST' })
      await refetch()
    } catch (error) {
      console.error('Failed to preload model:', error)
    }
  }

  const unloadModel = async (modelName: string) => {
    try {
      await fetch(`/api/v1/chat/models/unload/${encodeURIComponent(modelName)}`, { method: 'POST' })
      await refetch()
    } catch (error) {
      console.error('Failed to unload model:', error)
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Model Manager
          </h3>
          <div className="text-center py-8 text-gray-500">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
            <p>Loading models...</p>
          </div>
        </div>
      </div>
    )
  }

  const models = modelStatus?.models || []

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Model Manager
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          Manage installed Ollama models. Favorites are auto-loaded on startup for instant responses.
        </p>

        {models.length === 0 ? (
          <div className="p-6 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-center">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
              No models installed yet
            </p>
            <a
              href="https://ollama.com/library"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm"
            >
              <Download className="w-4 h-4" />
              <span>Browse Ollama Library</span>
            </a>
          </div>
        ) : (
          <div className="space-y-2">
            {models.map((model: any) => {
              const isFavorite = favorites.includes(model.name)
              const isLoaded = model.loaded || false

              return (
                <div
                  key={model.name}
                  className="flex items-center justify-between p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-primary-300 dark:hover:border-primary-700 transition-all"
                >
                  <div className="flex items-center gap-3 flex-1">
                    {/* Favorite star */}
                    <button
                      onClick={() => toggleFavorite(model.name)}
                      className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                      title={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
                    >
                      <Star
                        className={`w-4 h-4 ${
                          isFavorite
                            ? 'fill-yellow-400 text-yellow-400'
                            : 'text-gray-400 dark:text-gray-500'
                        }`}
                      />
                    </button>

                    {/* Model info */}
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {model.name}
                        </span>
                        {isFavorite && (
                          <span className="px-2 py-0.5 text-xs rounded-full bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200">
                            Favorite
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-3 mt-0.5">
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {model.size || 'Size unknown'}
                        </span>
                        {isLoaded && (
                          <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
                            <CheckCircle2 className="w-3 h-3" />
                            Loaded
                          </span>
                        )}
                        {!isLoaded && (
                          <span className="flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500">
                            <Circle className="w-3 h-3" />
                            Not loaded
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Load/Unload button */}
                    <button
                      onClick={() => isLoaded ? unloadModel(model.name) : preloadModel(model.name)}
                      className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                        isLoaded
                          ? 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                          : 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 hover:bg-primary-200 dark:hover:bg-primary-900/50'
                      }`}
                    >
                      {isLoaded ? 'Unload' : 'Load'}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* Download link */}
        {models.length > 0 && (
          <div className="mt-4 p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
            <p className="text-sm text-blue-900 dark:text-blue-100">
              Want more models?{' '}
              <a
                href="https://ollama.com/library"
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium underline hover:no-underline"
              >
                Browse Ollama Library
              </a>
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

function DangerZoneTab() {
  const [confirmInputs, setConfirmInputs] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState<Record<string, boolean>>({})

  const handleAction = async (action: string, endpoint: string, confirmText: string, successMsg: string) => {
    if (confirmInputs[action] !== confirmText) return

    setLoading({ ...loading, [action]: true })
    try {
      const response = await fetch(endpoint, { method: 'POST' })
      if (!response.ok) throw new Error(`${action} failed`)

      alert(successMsg)
      if (action === 'uninstall' || action === 'factory-reset') {
        window.location.reload()
      }
    } catch (error) {
      console.error(`${action} failed:`, error)
      alert(`Failed to ${action}`)
    } finally {
      setLoading({ ...loading, [action]: false })
      setConfirmInputs({ ...confirmInputs, [action]: '' })
    }
  }

  const DangerButton = ({
    action,
    endpoint,
    title,
    description,
    details,
    confirmText = 'CONFIRM',
    severity = 'medium'
  }: {
    action: string
    endpoint: string
    title: string
    description: string
    details?: string
    confirmText?: string
    severity?: 'safe' | 'medium' | 'high' | 'nuclear'
  }) => {
    const colors = {
      safe: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800 text-blue-900 dark:text-blue-100',
      medium: 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800 text-orange-900 dark:text-orange-100',
      high: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-900 dark:text-red-100',
      nuclear: 'bg-red-100 dark:bg-red-950/40 border-red-300 dark:border-red-900 text-red-950 dark:text-red-50'
    }

    const buttonColors = {
      safe: 'bg-blue-600 hover:bg-blue-700',
      medium: 'bg-orange-600 hover:bg-orange-700',
      high: 'bg-red-600 hover:bg-red-700',
      nuclear: 'bg-red-700 hover:bg-red-800'
    }

    return (
      <div className={`border-2 rounded-lg p-4 ${colors[severity]}`}>
        <h4 className="font-semibold mb-1 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          {title}
        </h4>
        <p className="text-sm mb-2">{description}</p>
        {details && <p className="text-xs opacity-80 mb-3">{details}</p>}

        <div className="flex gap-2">
          <input
            type="text"
            value={confirmInputs[action] || ''}
            onChange={(e) => setConfirmInputs({ ...confirmInputs, [action]: e.target.value })}
            placeholder={confirmText}
            className="flex-1 px-3 py-1.5 text-sm border-2 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border-gray-300 dark:border-gray-700"
          />
          <button
            onClick={() => handleAction(action, endpoint, confirmText, `${title} completed successfully`)}
            disabled={confirmInputs[action] !== confirmText || loading[action]}
            className={`px-4 py-1.5 text-sm text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors ${buttonColors[severity]}`}
          >
            {loading[action] ? 'Processing...' : 'Execute'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Export & Backup - Safe */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-blue-500"></span>
          Export & Backup
        </h3>
        <div className="space-y-3">
          <DangerButton
            action="export-all"
            endpoint="/api/admin/export-all"
            title="Export All Data"
            description="Download complete backup as ZIP"
            details="Includes: AI chats, team messages, query library, settings, and uploaded files"
            severity="safe"
          />
          <DangerButton
            action="export-chats"
            endpoint="/api/admin/export-chats"
            title="Export AI Chat History"
            description="Download all AI conversations as JSON"
            details="Preserves: messages, timestamps, models used, and file attachments"
            severity="safe"
          />
          <DangerButton
            action="export-queries"
            endpoint="/api/admin/export-queries"
            title="Export Query Library"
            description="Download saved SQL queries as JSON"
            details="Preserves: query names, folders, tags, and descriptions"
            severity="safe"
          />
        </div>
      </div>

      {/* Data Management - Medium Risk */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-orange-500"></span>
          Data Management
        </h3>
        <div className="space-y-3">
          <DangerButton
            action="clear-chats"
            endpoint="/api/admin/clear-chats"
            title="Clear AI Chat History"
            description="Delete all AI conversations"
            details="Preserves: settings and query library"
            severity="medium"
          />
          <DangerButton
            action="clear-team"
            endpoint="/api/admin/clear-team-messages"
            title="Clear Team Messages"
            description="Delete P2P chat history"
            details="Preserves: AI chats and query library"
            severity="medium"
          />
          <DangerButton
            action="clear-library"
            endpoint="/api/admin/clear-query-library"
            title="Clear Query Library"
            description="Delete all saved SQL queries"
            details="Preserves: query execution history"
            severity="medium"
          />
          <DangerButton
            action="clear-history"
            endpoint="/api/admin/clear-query-history"
            title="Clear Query History"
            description="Delete SQL execution history"
            details="Preserves: saved queries in library"
            severity="medium"
          />
          <DangerButton
            action="clear-temp"
            endpoint="/api/admin/clear-temp-files"
            title="Clear Temp Files"
            description="Delete uploaded files and exports"
            details="Frees up disk space without affecting data"
            severity="medium"
          />
          <DangerButton
            action="clear-code"
            endpoint="/api/admin/clear-code-files"
            title="Clear Code Editor Files"
            description="Delete saved code snippets"
            details="Preserves: all other data"
            severity="medium"
          />
        </div>
      </div>

      {/* Reset Options - High Risk */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-red-500"></span>
          Reset Options
        </h3>
        <div className="space-y-3">
          <DangerButton
            action="reset-settings"
            endpoint="/api/admin/reset-settings"
            title="Reset All Settings"
            description="Restore default settings"
            details="Preserves: all data (chats, queries, files)"
            confirmText="RESET"
            severity="high"
          />
          <DangerButton
            action="reset-data"
            endpoint="/api/admin/reset-data"
            title="Reset All Data"
            description="Delete all data, keep settings"
            details="Deletes: chats, queries, history, temp files"
            confirmText="DELETE"
            severity="high"
          />
          <DangerButton
            action="factory-reset"
            endpoint="/api/admin/reset-all"
            title="Factory Reset"
            description="Complete wipe - like first install"
            details="Deletes: everything (data + settings)"
            confirmText="DELETE"
            severity="high"
          />
        </div>
      </div>

      {/* Nuclear Options - Destructive */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-red-700"></span>
          Nuclear Options
        </h3>
        <div className="space-y-3">
          <DangerButton
            action="uninstall"
            endpoint="/api/admin/uninstall"
            title="Uninstall Application"
            description="Remove all app data permanently"
            details="Moves data to Trash/Recycle Bin. Cannot be undone."
            confirmText="DELETE"
            severity="nuclear"
          />
        </div>
      </div>
    </div>
  )
}

function ModelManagementTab() {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          Model Management Settings
        </h3>
        <div className="text-sm text-gray-600 dark:text-gray-400 space-y-3">
          <p>Configure global model behavior, default parameters, and auto-loading preferences.</p>
          <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <p className="text-sm text-blue-900 dark:text-blue-100 mb-2 font-medium">
              Model management settings are coming soon
            </p>
            <p className="text-xs text-blue-700 dark:text-blue-300">
              Configure default model parameters, auto-load preferences, memory limits, and context window settings.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
