import { useState, useEffect } from 'react'
import { X, Settings as SettingsIcon, Zap, AlertTriangle, Save, MessageSquare, Users2, Code2, Database } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as settingsApi from '@/lib/settingsApi'
import { type NavTab } from '@/stores/navigationStore'

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
  activeNavTab: NavTab
}

export function SettingsModal({ isOpen, onClose, activeNavTab }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<'settings' | 'power' | 'danger'>('settings')

  // Get tab-specific title and icon
  const getTabInfo = () => {
    switch (activeNavTab) {
      case 'team':
        return { icon: Users2, title: 'Team Chat Settings' }
      case 'chat':
        return { icon: MessageSquare, title: 'AI Chat Settings' }
      case 'editor':
        return { icon: Code2, title: 'Code Editor Settings' }
      case 'database':
        return { icon: Database, title: 'Database Settings' }
      default:
        return { icon: SettingsIcon, title: 'Settings' }
    }
  }

  const tabInfo = getTabInfo()

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
            <tabInfo.icon className="w-6 h-6 text-primary-600 dark:text-primary-400" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              {tabInfo.title}
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
            <span className="font-medium">Settings</span>
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
            <span className="font-medium">Power User</span>
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
          {activeTab === 'settings' && <SettingsTab activeNavTab={activeNavTab} />}
          {activeTab === 'power' && <PowerUserTab />}
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

  // Render tab-specific settings sections
  const renderTabSettings = () => {
    switch (activeNavTab) {
      case 'team':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                Team Chat Configuration
              </h3>
              <div className="text-sm text-gray-600 dark:text-gray-400 space-y-3">
                <p>Configure P2P team chat settings, encryption, and network preferences.</p>
                <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                  <p className="text-sm text-blue-900 dark:text-blue-100">
                    Team chat settings are coming soon. Stay tuned for peer-to-peer messaging, file sharing, and collaboration features.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )

      case 'chat':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                AI Chat Parameters
              </h3>
              <div className="text-sm text-gray-600 dark:text-gray-400 space-y-3">
                <p>Configure AI model parameters, temperature, context windows, and response behavior.</p>
                <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                  <p className="text-sm text-blue-900 dark:text-blue-100">
                    AI chat settings are coming soon. You'll be able to adjust temperature, top-k, top-p, context length, and system prompts.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )

      case 'editor':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                Code Editor Preferences
              </h3>
              <div className="text-sm text-gray-600 dark:text-gray-400 space-y-3">
                <p>Customize your code editor experience with themes, keybindings, and formatting options.</p>
                <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                  <p className="text-sm text-blue-900 dark:text-blue-100">
                    Editor settings are coming soon. Configure themes, font size, tab width, auto-formatting, and more.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )

      case 'database':
      default:
        // Database tab shows the full settings (existing content)
        return null
    }
  }

  const tabSpecificContent = renderTabSettings()

  return (
    <div className="space-y-8">
      {/* Show tab-specific content if available */}
      {tabSpecificContent ? (
        tabSpecificContent
      ) : (
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
      )}
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

function DangerZoneTab() {
  const [resetConfirm, setResetConfirm] = useState('')
  const [uninstallConfirm, setUninstallConfirm] = useState('')
  const [isResetting, setIsResetting] = useState(false)
  const [isUninstalling, setIsUninstalling] = useState(false)

  const handleReset = async () => {
    if (resetConfirm !== 'DELETE') return

    setIsResetting(true)
    try {
      const response = await fetch('/api/admin/reset-all', {
        method: 'POST',
      })
      if (!response.ok) throw new Error('Reset failed')

      alert('All data has been reset. Please refresh the page.')
      window.location.reload()
    } catch (error) {
      console.error('Reset failed:', error)
      alert('Failed to reset data')
      setIsResetting(false)
    }
  }

  const handleUninstall = async () => {
    if (uninstallConfirm !== 'DELETE') return

    if (!confirm('Are you ABSOLUTELY sure? This will delete all app data permanently.')) {
      return
    }

    setIsUninstalling(true)
    try {
      const response = await fetch('/api/admin/uninstall', {
        method: 'POST',
      })
      if (!response.ok) throw new Error('Uninstall failed')

      alert('App data has been uninstalled. You can now close this window.')
    } catch (error) {
      console.error('Uninstall failed:', error)
      alert('Failed to uninstall app')
      setIsUninstalling(false)
    }
  }

  return (
    <div className="space-y-8">
      <div className="bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-red-900 dark:text-red-100 mb-2 flex items-center space-x-2">
          <AlertTriangle className="w-5 h-5" />
          <span>Reset All Data</span>
        </h3>
        <p className="text-sm text-red-700 dark:text-red-300 mb-4">
          Clears all saved queries, resets settings to defaults. This action cannot be undone.
          You will start fresh as if using the app for the first time.
        </p>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-red-900 dark:text-red-100 mb-2">
              Type <strong>DELETE</strong> to confirm:
            </label>
            <input
              type="text"
              value={resetConfirm}
              onChange={(e) => setResetConfirm(e.target.value)}
              placeholder="DELETE"
              className="w-full px-3 py-2 border-2 border-red-300 dark:border-red-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
            />
          </div>
          <button
            onClick={handleReset}
            disabled={resetConfirm !== 'DELETE' || isResetting}
            className="w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isResetting ? 'Resetting...' : 'Reset Everything'}
          </button>
        </div>
      </div>

      <div className="bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-red-900 dark:text-red-100 mb-2 flex items-center space-x-2">
          <AlertTriangle className="w-5 h-5" />
          <span>Uninstall Application</span>
        </h3>
        <p className="text-sm text-red-700 dark:text-red-300 mb-4">
          Removes all app data and moves everything to Trash (macOS) or Recycle Bin (Windows).
          This action cannot be undone.
        </p>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-red-900 dark:text-red-100 mb-2">
              Type <strong>DELETE</strong> to confirm:
            </label>
            <input
              type="text"
              value={uninstallConfirm}
              onChange={(e) => setUninstallConfirm(e.target.value)}
              placeholder="DELETE"
              className="w-full px-3 py-2 border-2 border-red-300 dark:border-red-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
            />
          </div>
          <button
            onClick={handleUninstall}
            disabled={uninstallConfirm !== 'DELETE' || isUninstalling}
            className="w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isUninstalling ? 'Uninstalling...' : 'Uninstall App'}
          </button>
        </div>
      </div>
    </div>
  )
}
