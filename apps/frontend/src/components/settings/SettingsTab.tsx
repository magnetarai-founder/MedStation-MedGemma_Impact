import { useState, useEffect } from 'react'
import { Save } from 'lucide-react'
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
